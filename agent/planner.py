import json
import re

import anthropic

from typing import Optional
from observability.tracer import Tracer
from agent.prompts import PLANNER_PROMPT
from config import MODEL_NAME, CLIENT
from observability.logger import (
    log_planner_start, 
    log_planner_result,
    log_planner_end
)

def planner(question: str, tracer: Optional[Tracer] = None, is_replan: bool = False) -> list[dict]:
    """
    Send a question to the LLM and parse the response into a list of plan steps.

    Constructs a single-turn message using the provided question, calls the
    Claude API with a predefined planner system prompt, and extracts a JSON
    array from the response text. The JSON array is expected to represent a
    sequence of plan steps.

    Args:
        question: The user's input question or task to be planned.
        tracer: Optional tracer for logging planner invocation and results.
        is_replan: Whether this call is a replan rather than an initial plan.

    Returns:
        A list of dicts, where each dict represents a single step in the plan
        as returned by the model.

    Raises:
        ValueError: If question is empty or not a string, if the API request
            is invalid, if the response contains no JSON array, if the
            extracted JSON cannot be parsed, or if the parsed JSON is not a
            list of dicts.
        RuntimeError: If API authentication fails, the rate limit is exceeded,
            the connection fails, the API returns an error status, or the
            response is empty or malformed.
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError(f"Question must be a non-empty string, got: {repr(question)}")

    tracer = tracer or Tracer(filepath=None, run_id=None)

    log_planner_start(question)
    
    tracer.log_planner_called(prompt=question, is_replan=is_replan)

    try:
        response = CLIENT.messages.create(
            model=MODEL_NAME,
            max_tokens=1024,
            system=PLANNER_PROMPT,
            messages=[{'role': 'user', 'content': question}]
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
        match = re.search(r'\[.*\]', raw, re.DOTALL)
    except (IndexError, AttributeError):
        raise RuntimeError("API response was empty or malformed.")
    
    if match:
        raw = match.group(0).strip()
    else:
       raise ValueError("Model returned string that didn't contain a valid JSON array")
    
    try:
        steps = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Planner returned invalid JSON: {e}\nRaw output:\n{raw}")

    if not isinstance(steps, list) or not all(isinstance(step, dict) for step in steps):
        raise ValueError(f"Expected a list of dicts, got: {raw}")

    tracer.log_planner_result(steps=steps, is_replan=is_replan)

    log_planner_result(steps)
    log_planner_end()

    return steps