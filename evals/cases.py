from config import EVAL_FIXTURES_PATH


starting_code_buggy = (EVAL_FIXTURES_PATH / 'task_manager_buggy.py').read_text(encoding="utf-8")
starting_code_correct = (EVAL_FIXTURES_PATH / 'task_manager_correct.py').read_text(encoding="utf-8")

EVAL_CASES = [
    #{
    #    "id": "q1",
    #    "question": "Fix the bug in the task_manager.py",
    #    "starting_code": starting_code_buggy,
    #    "expect_success": True,
    #},
    #
    #{
    #    "id": "q2",
    #    "question": "Can you find a bug in task_manager.py",
    #    "starting_code": starting_code_buggy,
    #    "expect_success": True,
    #},
    #
    #{
    #    "id": "q3",
    #    "question": "What is the bug in manager_of_tasks.py",
    #    "starting_code": starting_code_buggy,
    #    "expect_success": True,
    #},
#
    #{
    #    "id": "q4",
    #    "question": "Where is the bug in web_scraper.py",
    #    "starting_code": starting_code_buggy,
    #    "expect_success": False,
    #},

    # q5 tests regression detection, not bug-fixing: starting_code is already
    # correct (9/9 passing). The agent is asked to add a feature likely to
    # break things as a side effect. If it does, 3 tests fail, but not for
    # the same reason — test_add_task_returns_correct_title and
    # test_get_all_tasks_returns_task_list fail directly (title correctness
    # IS what they check). test_get_pending_tasks_returns_pending_tasks_only
    # fails collaterally — its real subject is filtering logic, which still
    # works; its title-based assertion just happens to depend on a string
    # the agent changed. expect_success=True means the run should still end
    # with all 9 tests green — via the reflector catching the regression
    # (new test failures) and triggering a replan, not via the agent
    # avoiding the regression on the first attempt.
    {
        "id": "q5",
        "question": "Add a timestamp to the task title when a task is created",
        "starting_code": starting_code_correct,
        "expect_success": True,
    }
]