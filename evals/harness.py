import time
import subprocess
import uuid
import json

from typing import Optional, Any
from datetime import datetime, timezone

from agent.tools import write_file
from agent.agent import agent
from evals.cases import EVAL_CASES
from config import WORKSPACE_PATH, EVAL_RESULTS_PATH, TRACES_PATH


def _run_pytest_check(file_name: str) -> int:
    """Run pytest against a file in the workspace and return its exit code.

    Args:
        file_name: Name of the file (relative to WORKSPACE_PATH) to test.

    Returns:
        The pytest process's return code (0 means all tests passed).

    Raises:
        RuntimeError: If invoking the pytest subprocess itself fails
            (e.g. OS-level error), as distinct from the tests merely
            failing.
    """
    try:
        result = subprocess.run(
            ['pytest', str(WORKSPACE_PATH / file_name)],
            capture_output=True,
            encoding='utf-8'
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"Failed to run pytest on {file_name}: {exc}") from exc
    return result.returncode 


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    """Run a single agent evaluation case and report whether it passed.

    Resets `task_manager.py` to the case's starting code, runs the agent on
    the case's question, and checks the result against expectations:

    - If `expect_success` is True: the agent must not raise, and running
      pytest on `test_task_manager.py` afterward must succeed (return code 0).
    - If `expect_success` is False: the agent is expected to raise a
      RuntimeError whose message contains "Replanner returned an empty step
      list" (i.e. it correctly determined there was nothing to fix).

    Args:
        case: Dict describing the test case. Required keys:
            - "id": Case identifier.
            - "question": Prompt/question to pass to the agent.
            - "starting_code": Source code to write to task_manager.py before
              invoking the agent.
            - "expect_success": Whether the agent is expected to fix the code
              successfully (True) or correctly give up (False).

    Returns:
        Dict with keys:
            - "id": The case id.
            - "question": The case question.
            - "passed": Whether the outcome matched expectations.
            - "reason": Human-readable explanation of the result.
            - "elapsed": Time in seconds the case took to run.
            - "error": String form of any exception encountered, or None.

    Raises:
        KeyError: If `case` is missing one of the required keys.
    """
    t0 = time.time()

    try:
        case_id = case["id"]
        question = case["question"]
        starting_code = case["starting_code"]
        expect_success = case["expect_success"]
    except KeyError as exc:
        raise KeyError(f"Test case is missing required key: {exc}") from exc
    
    reset_result = write_file('task_manager.py', starting_code)
    if reset_result.startswith("Error:"):
        passed = False
        reason = f"Could not reset workspace: {reset_result}"
        return {
            "id": case_id,
            "question": question,
            "passed": passed,
            "reason": reason,
            "elapsed": time.time() - t0,
            "error": reset_result,
        }

    e: Optional[Exception] = None
    agent_run_info = {}
    replan_counter = 0
    try:
        agent(question, run_info=agent_run_info)
        agent_raised = False
    except Exception as exc:
        agent_raised = True
        e = exc

    try:
        with open(TRACES_PATH, 'r', encoding='utf-8') as f:
            if "run_id" in agent_run_info:
                for line in f.readlines():
                    raw_line = json.loads(line)
                    if raw_line['run_id'] == agent_run_info['run_id'] and raw_line['event'] == 'replan_triggered':
                        replan_counter += 1
    except FileNotFoundError:
        replan_counter = 0

    if expect_success:
        if agent_raised:
            passed = False
            reason = f'Expected success, agent raised: {e}'
        else:
            try:
                test_result = _run_pytest_check("test_task_manager.py")
            except RuntimeError as exc:
                passed = False
                reason = f"Could not verify fix: {exc}"
                e = exc
            else:
                if test_result == 0:
                    passed = True
                    reason = 'All tests passed after fix'
                else:
                    passed = False
                    reason = "Tests still failing after agent ran"
    else:
        if agent_raised and isinstance(e,RuntimeError) and "Replanner returned an empty step list" in str(e):
            passed = True
            reason = "Agent correctly gave up - no file/bug found"
        else:
            passed = False
            reason = f"Expected empty-step-list error, got {e if e else 'no error'}"
    
    elapsed = time.time() - t0
    return {
            "id": case_id,
            "question": question,
            "passed": passed,
            "reason": reason,
            "elapsed": elapsed,
            "replan_count": replan_counter,
            "error": str(e) if e else None,
        }

def run_eval(cases: list[dict]) -> None:
    """
    Run a batch of evaluation cases and write results to disk.

    Executes each case in cases sequentially via run_case, prints
    per-case progress and a final summary report to stdout, and
    appends a JSON-lines record for every result to
    EVAL_RESULTS_PATH, tagged with a shared eval_run_id and UTC
    timestamp. A failure to write the results file is caught and printed as a
    warning rather than raised.

    Args:
        cases (list[dict]): List of eval case dicts, each expected to
            contain at least 'id' (str) and 'question' (str) keys.

    Returns:
        None

    Raises:
        KeyError: If a case in `cases` is missing a required key
            (e.g. 'id', 'question'). Raised either by the direct
            dict access in this function or propagated from
            `run_case`; deliberately left uncaught — a malformed
            case dict is a bug in `cases.py`, not a runtime
            condition this function should handle.
    """
    eval_run_id = uuid.uuid4().hex[:8]
    print(f"Running {len(cases)} eval cases... (run_id: {eval_run_id})")
    t0 = time.time()
    results: list[dict[str, Any]] = []

    for i, case in enumerate(cases, 1):
        print(f"  [{i}/{len(cases)}] {case['id']}: {case['question']}")
        result = run_case(case)
        results.append(result)
        print(f"  --> {'PASS' if result['passed'] else 'FAIL'} ({result['elapsed']}s)")
        print()

    try:
        with open(EVAL_RESULTS_PATH, 'a', encoding='utf-8') as f:
            for r in results:
                record = {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "eval_run_id": eval_run_id,
                    **r
                }
                f.write(json.dumps(record) + "\n")
    except OSError as e:
        print(f"Warning: failed to write results to {EVAL_RESULTS_PATH}: {e}")

    passed = sum(1 for r in results if r["passed"])
    print(f"\n--- EVAL REPORT ---")
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"[{status}] {r['id']} ({r['elapsed']}s)")
        print(f"     Question:   {r['question']}")
        print(f"       Passed:   {r['passed']}")
        print(f"       Reason:   {r['reason']}")
        print(f" Replan count:   {r['replan_count']}")
        if r["error"]:
            print(f"  Error:   {r['error']}")
        print()
    print(f"Result: {passed}/{len(results)} passed in {time.time() - t0:.1f}s")

if __name__ == '__main__': 
    run_eval(EVAL_CASES)