from agent.planner import planner
from agent.executor import executor
from observability.logger import log_agent_start, log_agent_end

def agent(question: str) -> str:
    """
    Runs a question through the planner and executor to produce an answer.

    Generates a step-by-step plan for the given question and executes each
    step in sequence, returning the final result.

    Args:
        question (str): The question to answer. Must be a non-empty string.

    Returns:
        str: The final answer produced after executing all planned steps.

    Raises:
        ValueError: If ``question`` is not a non-empty string.
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError(f"Question must be a non-empty string, got: {repr(question)}")

    log_agent_start()
    steps = planner(question=question)
    result = executor(steps=steps, question=question)
    
    log_agent_end()
    return result