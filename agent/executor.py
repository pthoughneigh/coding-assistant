import json
import re
import time

import anthropic

from typing import Any, Optional
from observability.tracer import Tracer
from agent.tools import search_code, read_file, write_file, run_tests
from agent.prompts import STEP_TRANSLATOR_PROMPT
from agent.reflector import reflector
from agent.planner import planner
from config import CLIENT, MODEL_NAME, MAX_REPLANS
from observability.logger import (
    log_translator_start,
    log_translator_result,
    log_executor_start,
    log_executor_end
)


def run_tool(tool_name: str, inputs: dict[str, Any]) -> str:
    """
    Dispatch a named tool call with the provided input arguments.

    Looks up ``tool_name`` in the internal tool registry and invokes the
    corresponding function with ``inputs`` unpacked as keyword arguments.
    Returns a plain-text result or an error message if the tool is not found
    or a required input field is missing.

    Args:
        tool_name: The registered name of the tool to execute. Must be one of
            ``"search_code"``, ``"read_file"``, ``"write_file"``, or
            ``"run_tests"``.
        inputs: A mapping of keyword argument names to values that will be
            forwarded to the selected tool via ``**inputs``.

    Returns:
        The string output produced by the tool, or an error message prefixed
        with ``"Error:"`` if the tool name is not found or a required input
        field is absent.

    Raises:
        No exceptions are raised; all ``KeyError`` cases are caught internally
        and returned as error strings.
    """
    tools = {
        'search_code': search_code,
        'read_file': read_file,
        'write_file': write_file,
        'run_tests': run_tests
    }
    try:
        tool = tools[tool_name]
    except KeyError as e:
        return f"Error: Tool does not exist in the tool dictionary: - {e}"
    try:
        return tool(**inputs)
    except KeyError as e:
        return f"Error: missing required input field: - {e}"
    
def step_translator(
    question: str,
    step: dict[str, Any],
    prior_outputs: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Translate a single plan step into a concrete tool-input dict via an LLM call.

    Builds a structured prompt from the current step, the original question, and
    any prior step outputs, then calls the Claude API using STEP_TRANSLATOR_PROMPT
    as the system prompt. The model is expected to return a raw JSON object whose
    keys match the target tool's input schema.

    Args:
        question: The original user question driving the overall plan.
        step: A dict describing the current plan step. Expected keys:
            - ``"step"`` (int): the step number.
            - ``"tool"`` (str): the tool to call (e.g. ``"read_file"``).
            - ``"description"`` (str): a natural-language description of what
              this step should accomplish.
        prior_outputs: Results collected from all preceding steps. Each entry
            is a dict with keys:
            - ``"step"`` (int): the step number that produced this output.
            - ``"tool"`` (str): the tool that was called.
            - ``"output"`` (str): the string result returned by that tool.

    Returns:
        A dict of keyword arguments ready to be unpacked and passed to
        ``run_tool`` — keys and value types match the target tool's input schema.

    Raises:
        ValueError: If the API request was malformed, the model's response
            contained no JSON object, or the extracted JSON failed to parse.
        RuntimeError: If the API call failed due to an authentication error,
            rate limit, connection problem, or unexpected status code, or if
            the response was empty or malformed.
    """
    context = "\n\n".join(
                    f"Step {o['step']} ({o['tool']}) output:\n{o['output']}"
                    for o in prior_outputs
                )
    
    prior_steps = f"Prior step outputs:\n{context}" if context else "No prior steps yet."

    user_message = (
                    f"User question: {question}\n\n"
                    f"Current step {step['step']}: call tool \"{step['tool']}\"\n"
                    f"Step description: {step['description']}\n\n"
                    f"{prior_steps}\n\n"
                    + f"Return the JSON input for the \"{step['tool']}\" tool."
                )
    
    log_translator_start(step, user_message=user_message)

    try: 
        response = CLIENT.messages.create(
            model=MODEL_NAME,
            max_tokens=1024,
            system=STEP_TRANSLATOR_PROMPT,
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
       raise ValueError("Model returned string that didn't contain a valid JSON object")

    try:
        arguments = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Step translator returned invalid JSON: {e}\nRaw output:\n{raw}")
    
    log_translator_result(arguments)

    return arguments


def executor(steps: list[dict], question: str, tracer: Optional[Tracer] = None) -> str:
    """
    Execute a sequence of tool-based steps to answer a question.

    Iterates over a plan of steps, translating each into tool arguments using
    prior context, running the tool, and accumulating outputs. After each step
    (except ``run_tests``), a reflector judges the result and may trigger a
    replan — replacing the remaining steps with a revised plan and restarting
    the loop. Raises an error if replanning occurs more than ``MAX_REPLANS``
    times. Returns the result of the final step.

    Args:
        steps: A non-empty list of step dicts, each containing at least:
            - ``step`` (int): The step index.
            - ``tool`` (str): The name of the tool to invoke.
            - ``description`` (str): What the step is meant to do.
        question: The original question driving the execution. Must be
            a non-empty string.
        tracer: Optional tracer for logging execution events. 
            Defaults to a no-op tracer if not provided.

    Returns:
        The output of the last step's tool call.

    Raises:
        ValueError: If ``steps`` is empty or ``question`` is not a non-empty
            string.
        RuntimeError: If replanning is triggered more than ``MAX_REPLANS``
            times, indicating the executor could not make progress.
    """
    tracer = tracer or Tracer(filepath=None, run_id=None)
    prior_outputs = []
    replan_count = 0
    
    if not steps:
        raise ValueError(f"Steps must be a non-empty list, got: {repr(steps)}")
    
    if not isinstance(question, str) or not question.strip():
        raise ValueError(f"Question must be a non-empty string, got: {repr(question)}")
    
    log_executor_start()
    
    while True: 
        for step in steps:
            tracer.log_step_start(step=step)
            
            arguments = step_translator(question=question, step=step, prior_outputs=prior_outputs)
            
            tracer.log_translator_result(step_num=step['step'], tool=step['tool'], tool_input=arguments)

            t0_tool = time.time()
            result = run_tool(step['tool'], arguments)
            elapsed = time.time() - t0_tool

            tracer.log_tool_result(step['step'], step['tool'], output=result, elapsed=elapsed)

            prior_outputs.append({'step': step['step'], 'tool': step['tool'], 'output': result})

            if step['tool'] != 'run_tests':
                verdict = reflector(question=question, step=step, prior_outputs=prior_outputs, curr_step_result=result)

                tracer.log_reflector_verdict(step_num=step['step'], verdict=verdict)
                
                if verdict['decision'] == 'replan':
                    replan_count += 1
                    if replan_count > MAX_REPLANS:

                        tracer.log_executor_gave_up(replan_count=replan_count, reason=verdict['reason'])
                        
                        raise RuntimeError(
                                f"Executor gave up after {MAX_REPLANS} replans. "
                                f"Last failure: {verdict['reason']}")
                    
                    tracer.log_replan_triggered(replan_count=replan_count, reason=verdict['reason'], prior_outputs=prior_outputs)
                    
                    steps = planner(
                            question
                            + f"\n\nNote for replanner: {verdict['reason']}\n\n"
                            + "Steps completed so far:\n"
                            + "\n".join(
                                f"  {o['step']}. [{o['tool']}] output: {o['output'][:200]}"
                                for o in prior_outputs
                            )
                            + f"\n\nReturn ONLY the remaining steps still needed. Do not repeat completed steps."
                            + f" Start step numbering from {len(prior_outputs) + 1}."
                            + " The first step does not need to be read_file or search_code — continue from where the plan left off.",
                            tracer=tracer,
                            is_replan=True
                            
                    )
                    if not steps:
                        raise RuntimeError(f"Replanner returned an empty step list - {verdict['reason']}")
                    
                    break
        else:
            break

    log_executor_end(result=result)

    return result