from datetime import datetime
from typing import Any
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[31m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    BLUE    = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN    = "\033[36m"
    WHITE   = "\033[37m"

    def __init__(self):
        raise TypeError("C is a namespace, not meant to be instantiated")


# ── Planner ───────────────────────────────────────────────────────────────────
TOOL_COLORS = {
    "read_file": C.GREEN,
    "search_code": C.RED,
    "write_file": C.YELLOW,
    "run_tests": C.BLUE
}

def _ts() -> str:
    return f"{C.DIM}{datetime.now().strftime('%H:%M:%S')}{C.RESET}"

# ---PLANNER-----------------------------------------------------
def log_planner_start(question: str) -> None:
    print(f"{C.MAGENTA}  ┌ PLANNER{C.RESET} Started at: {_ts()}")
    print(f"{C.MAGENTA}  │ Question:{C.RESET} {question}")

def log_planner_result(steps: list[dict]) -> None:
    print(f"{C.MAGENTA}  │{C.RESET} Generated: {C.BOLD}{len(steps)} steps:{C.RESET}")
    for s in steps:
        tool_color = TOOL_COLORS.get(s['tool'], C.WHITE)
        print(f"{C.MAGENTA}  │{C.RESET}   {C.DIM}{s['step']:>2}.{C.RESET} [{tool_color}{s['tool']}{C.RESET}] - {s['description']}")

def log_planner_end() -> None:
    print(f"{C.MAGENTA}  │ Planner finished at:{C.RESET}  {_ts()}")
    print(f"{C.MAGENTA}  └{'─' * 60}{C.RESET}")
    print()


# ---STEP TRANSLATOR-----------------------------------------------
def log_translator_start(step: dict[str, Any], user_message: str):
    print(f"{C.MAGENTA}  ┌ Step translator{C.RESET} Started at: {_ts()}")
    tool_color = TOOL_COLORS.get(step['tool'], C.WHITE)
    print(f"{C.MAGENTA}  │{C.RESET}   {C.DIM}Step{step['step']:>2}.{C.RESET} [{tool_color}{step['tool']}{C.RESET}]")
    print(f"{C.MAGENTA}  │ User message: {C.MAGENTA}\n  │   {C.RESET}{user_message[:300].replace('\n', f'{C.MAGENTA}\n  │   {C.RESET}')}")
  

def log_translator_result(inputs: dict[str, Any]):
    print(f"{C.MAGENTA}  │ Step translator output: {C.RESET}")
    for i in inputs.keys():
        print(f"{C.MAGENTA}  │   {C.CYAN}{i}: - {C.MAGENTA}\n  │{C.GREEN}\t{inputs[i][:200].replace('\n', f'{C.MAGENTA}\n  │   {C.GREEN}\t')}")
    print(f"{C.MAGENTA}  │ Step translator finished at:{C.RESET} {_ts()}")
    print(f"{C.MAGENTA}  └{'─' * 60}{C.RESET}")
    print()


# ---EXECUTOR-------------------------------------------------------
def log_executor_start(question: str) -> None:
    print(f"{C.MAGENTA}  ┌ Executor{C.RESET} Started at: {_ts()}")
    print(f"{C.MAGENTA}  │ Question:{C.RESET} {question}")

def log_executor_end(result: str) -> None:
    print(f"{C.MAGENTA}  │ Executor last result: {C.RESET} {C.MAGENTA}\n  │{C.RESET}\t{result.replace('\n', f'{C.MAGENTA}\n  │   {C.RESET}\t')}")
    print(f"{C.MAGENTA}  │ Executor finished at:{C.RESET}  {_ts()}")
    print(f"{C.MAGENTA}  └{'─' * 60}{C.RESET}")
    print()
