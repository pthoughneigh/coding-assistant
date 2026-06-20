import uuid
import time 

from typing import Optional
from config import TRACES_PATH
from observability.tracer import Tracer
from agent.planner import planner
from agent.executor import executor
from observability.logger import log_agent_start, log_agent_end

def agent(question: str, run_info: Optional[dict] = None) -> str:
    """
    Runs a question through the planner and executor to produce an answer.

    Generates a step-by-step plan for the given question and executes each
    step in sequence, returning the final result.

    Args:
        question (str): The question to answer. Must be a non-empty string.
        run_info (Optional[dict]): If provided, this function writes the
            generated `run_id` into it under the key `'run_id'`, so the
            caller can later look up this run's trace events in
            TRACES_PATH. Has no effect on the function's behavior or
            return value. Defaults to None.

    Returns:
        str: The final answer produced after executing all planned steps.

    Raises:
        ValueError: If ``question`` is not a non-empty string.
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError(f"Question must be a non-empty string, got: {repr(question)}")
    
    t0 = time.time()
    run_id = uuid.uuid4().hex[:8]
    if run_info is not None:
        run_info['run_id'] = run_id

    log_agent_start()

    with Tracer(run_id=run_id, filepath=TRACES_PATH) as tracer:
        tracer.log_agent_start(question=question)
        try:
            steps = planner(question=question, tracer=tracer, is_replan=False)
            result = executor(steps=steps, question=question, tracer=tracer)
            tracer.log_agent_end(answer=result, elapsed=time.time() - t0, success=True)
            log_agent_end()
        except Exception as e:
            tracer.log_unexpected_error(stage='agent', exc=e)
            tracer.log_agent_end(answer=str(e), elapsed=time.time() - t0, success=False)
            log_agent_end()
            raise

    return result