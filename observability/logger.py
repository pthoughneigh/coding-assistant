from datetime import datetime
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


