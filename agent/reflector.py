import json
import re
from typing import Any
from config import CLIENT, MODEL_NAME
from agent.prompts import REFLECTOR_PROMPT
from observability.logger import log_reflector_start, log_reflector_user_message, log_reflector_end

import anthropic

def reflector(question: str, step: dict[str, Any], prior_outputs: list[dict[str, Any]], curr_step_result: str) -> dict[str, Any]:
    """
    Evaluate a step's result and decide whether to continue or replan.

    Calls the LLM with the current question, step metadata, prior step outputs,
    and the current step's result. The model acts as a reflector, judging whether
    the result is sufficient to proceed or whether the plan needs to be revised.

    Args:
        question: The original user question driving the agent.
        step: The current plan step, with keys:
            - ``step`` (int): step index
            - ``tool`` (str): tool that was called
            - ``description`` (str): what the step was meant to do
        prior_outputs: Outputs from all previously completed steps, each a dict with:
            - ``step`` (int): step index
            - ``tool`` (str): tool used
            - ``output`` (str): result of that step
        curr_step_result: The string output produced by the current step's tool call.

    Returns:
        A dict with exactly two keys:
            - ``decision`` (str): either ``'continue'`` or ``'replan'``
            - ``reason`` (str): the model's justification for the decision

    Raises:
        ValueError: If inputs are invalid, the API response contains no JSON
            object, the JSON is malformed, or the returned dict has unexpected
            keys or an invalid decision value.
        RuntimeError: If the API call fails due to authentication, rate limiting,
            connection issues, or an unexpected response format.
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError(f"Question must be a non-empty string, got: {repr(question)}")
    
    if not isinstance(curr_step_result, str) or not curr_step_result.strip():
        raise ValueError(f"Current step result must be a non-empty string, got: {repr(curr_step_result)}")
    
    log_reflector_start()

    context = "\n\n".join(
                    f"Step {o['step']} ({o['tool']}) output:\n{o['output']}"
                    for o in prior_outputs)

    prior_steps = f"Prior step outputs:\n{context}" if context else "No prior steps yet."

    user_message = (
        f"Original user request (for context only — the plan below already interprets it; "
        f"do not re-derive intent from this text): {question}\n\n"
        f"{prior_steps}\n\n"
        f"Current step {step['step']}: call tool \"{step['tool']}\"\n"
        f"Step description: {step['description']}\n\n"
        f"Judge this step's result against its description and the rules — "
        f"not against a literal re-reading of the original request:\n{curr_step_result}\n\n"
        f"Return a valid JSON object with exactly two keys: decision and reason"
    )

    log_reflector_user_message(user_message)

    try: 
        response = CLIENT.messages.create(
            model=MODEL_NAME,
            max_tokens=1024,
            system=REFLECTOR_PROMPT,
            messages=[{'role': 'user', 'content': user_message}]
        )
    except anthropic.BadRequestError as e:
        raise ValueError(f"Invalid request to API: {e}")
    except anthropic.AuthenticationError as e:
        raise RuntimeError(f"API authentication failed: {e}")
    except anthropic.RateLimitError as e:
        raise RuntimeError(f"API rate limit exceeded: {e}")
    except anthropic.APIConnectionError as e:
        raise RuntimeError(f"Failed to connect to API: {e}")
    except anthropic.APIStatusError as e:
        raise RuntimeError(f"API returned error status {e.status_code}: {e}")


    try:
        raw = response.content[0].text.strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
    except (IndexError, AttributeError):
        raise RuntimeError("API response was empty or malformed.")
    
    if match:
        raw = match.group(0).strip()
    else:
       raise ValueError("Reflector returned string that didn't contain a valid JSON object")
    
    try:
        verdict = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Reflector returned invalid JSON: {e}\nRaw output:\n{raw}")
    
    
    if verdict.keys() == {'decision', 'reason'} and verdict['decision'] in ('continue', 'replan'):
        log_reflector_end(verdict)
        return verdict
    else:
        raise ValueError(f"Reflector returned invalid dictionary - {verdict}")