import textwrap
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
    ORANGE  = "\033[38;5;173m"  # warm orange        — Agent (outermost)
    GOLD    = "\033[38;5;178m"  # warm gold          — Planner
    RUST    = "\033[38;5;130m"  # burnt rust         — Executor  
    CORAL   = "\033[38;5;209m"  # light coral/salmon — Step Translator
    CREAM   = "\033[38;5;223m"  # warm cream         — labels/headings
    SAGE    = "\033[38;5;108m"  # muted green        — Reflector

    def __init__(self):
        raise TypeError("C is a namespace, not meant to be instantiated")

def _ts() -> str:
    return f"{C.DIM}{datetime.now().strftime('%H:%M:%S')}{C.RESET}"

TOOL_COLORS = {
    "read_file": C.GREEN,
    "search_code": C.RED,
    "write_file": C.YELLOW,
    "run_tests": C.BLUE
}

# ── PLANNER───────────────────────────────────────────────────────────────────
def log_planner_start(question: str) -> None:
    print(f"{C.ORANGE}  ┌ {C.GOLD}PLANNER{C.RESET} Started at: {_ts()}")
    print(f"{C.ORANGE}  │ {C.CREAM}Question:{C.RESET}")
    for paragraph in question[:500].splitlines():
        for line in textwrap.wrap(paragraph, width=100) or [paragraph]:
            print(f"{C.ORANGE}  │   {C.RESET}{line}{C.RESET}")
    print(f"{C.ORANGE}  │{C.RESET}")

def log_planner_result(steps: list[dict]) -> None:
    print(f"{C.ORANGE}  │{C.CREAM} Generated: {C.RESET}{C.WHITE}{len(steps)} steps:{C.RESET}")
    for s in steps:
        tool_color = TOOL_COLORS.get(s['tool'], C.WHITE)
        print(f"{C.ORANGE}  │{C.RESET}   {C.DIM}{s['step']:>2}.{C.RESET} [{tool_color}{s['tool']}{C.RESET}] - {s['description']}")

def log_planner_end() -> None:
    print(f"{C.ORANGE}  │ {C.GOLD}Planner {C.WHITE}finished at:{C.RESET}  {_ts()}")
    print()


# ── STEP TRANSLATOR────────────────────────────────────────────────────────────
def log_translator_start(step: dict[str, Any], user_message: str) -> None:
    print(f"{C.ORANGE}  ┌ {C.CORAL}Step translator{C.RESET} Started at: {_ts()}")
    tool_color = TOOL_COLORS.get(step['tool'], C.WHITE)
    print(f"{C.ORANGE}  │{C.RESET}   {C.DIM}Step{step['step']:>2}.{C.RESET} [{tool_color}{step['tool']}{C.RESET}]")
    print(f"{C.ORANGE}  │ {C.CREAM}User message: {C.ORANGE}\n  │   {C.RESET}{user_message[:300].replace('\n', f'{C.ORANGE}\n  │   {C.RESET}')}")
  

def log_translator_result(inputs: dict[str, Any]) -> None:
    print(f"{C.ORANGE}  │ {C.CREAM}Step translator output:{C.RESET}")
    for key, value in inputs.items():
        print(f"{C.ORANGE}  │   {C.CYAN}{key}:{C.RESET}")
        for line in str(value)[:200].splitlines():
            print(f"{C.ORANGE}  │     {C.GREEN}{line}{C.RESET}")
    print(f"{C.ORANGE}  │ {C.CORAL}Step translator {C.WHITE}finished at:{C.RESET} {_ts()}")
    print()


# ── EXECUTOR────────────────────────────────────────────────────────────────────
def log_executor_start() -> None:
    print(f"{C.ORANGE}  ┌ {C.RUST} Executor{C.RESET} Started at: {_ts()}")
    print()

def log_executor_end(result: str) -> None:
    print(f"{C.ORANGE}  │ {C.CREAM}Executor last result: {C.RESET} {C.ORANGE}\n  │{C.RESET}\t{result.replace('\n', f'{C.ORANGE}\n  │   {C.RESET}\t')}")
    print(f"{C.ORANGE}  │ {C.RUST}Executor {C.WHITE}finished at:{C.RESET}  {_ts()}")
    print()

# ── REFLECTOR────────────────────────────────────────────────────────────────────
def log_reflector_start() -> None:
    print(f"{C.ORANGE}  ┌ {C.SAGE} Reflector{C.RESET} Started at: {_ts()}")
    print()

def log_reflector_user_message(user_message: str) -> None:
    print(f"{C.ORANGE}  │ {C.CREAM}User message: {C.ORANGE}\n  │   {C.RESET}{user_message[:300].replace('\n', f'{C.ORANGE}\n  │   {C.RESET}')}")

def log_reflector_end(result: dict[str, Any]) -> None:
    for key, value in result.items():
        print(f"{C.ORANGE}  │   {C.CYAN}{key}:{C.RESET}")
        for line in str(value)[:200].splitlines():
            print(f"{C.ORANGE}  │     {C.GREEN}{line}{C.RESET}")
    print(f"{C.ORANGE}  │ {C.SAGE}Reflector {C.WHITE}finished at:{C.RESET} {_ts()}")
    print()

# ── AGENT────────────────────────────────────────────────────────────────────────
def log_agent_start() -> None:
    print(f"{C.ORANGE}  ┌ Agent{C.RESET} Started at: {_ts()}")
    print()

def log_agent_end() -> None:
    print(f"{C.ORANGE}  │ Agent{C.RESET} {C.WHITE}finished at: {_ts()}")
    print(f"{C.ORANGE}  └{'─' * 60}{C.RESET}")