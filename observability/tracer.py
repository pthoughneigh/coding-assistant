import json
import datetime

from pathlib import Path
from typing import Optional


class Tracer:
    """
    A context manager for appending structured JSON event traces to a log file.

    Each record is written as a newline-delimited JSON entry containing a UTC
    timestamp, the run identifier, an event name, and an arbitrary payload dict.

    Attributes:
        run_id (Optional[str]): Identifier for the current run, included in every record.
        filepath (Optional[Path]): Path to the log file being written to, or None in no-op mode.
    """
    def __init__(self,  filepath: Optional[Path] = None, run_id: Optional[str] = None) -> None:
        self.run_id = run_id
        self.filepath = filepath
        if run_id is None or filepath is None:
            self._file = None
            return
        self._file = open(filepath, "a", encoding="utf-8")

    def __enter__(self) -> "Tracer":
        """Return the Tracer instance for use as a context manager."""
        return self

    def __exit__(self, *args) -> None:
        """Flush and close the log file on context exit."""
        if self._file is not None:
            self._file.close()

    def _write(self, event: str, payload: dict) -> None:
        """
        Serialize and append a single trace record to the log file.

        The record is written as a JSON object on one line, immediately flushed
        to disk. Any serialization or I/O error is silently suppressed.

        Args:
            event (str): Name of the event being recorded.
            payload (dict): Arbitrary data associated with the event.
        """
        if self._file is None:
            return
        
        record = {
                "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "run_id": self.run_id,
                "event": event,
                "payload": payload
            }
        try:
            self._file.write(json.dumps(record) + "\n")
            self._file.flush()
        except Exception:
            pass

    # ── Agent ─────────────────────────────────────────────────────────────────
    def log_agent_start(self, question: str) -> None:
        self._write("agent_start", {"question": question})

    def log_agent_end(self, answer: str, elapsed: float, success: bool) -> None:
        self._write("agent_end", {
            "answer": answer,
            "elapsed": round(elapsed, 3),
            "success": success
        })

    # ── Planner ───────────────────────────────────────────────────────────────
    def log_planner_called(self, prompt: str, is_replan: bool) -> None:
        self._write("planner_called", {
            "prompt": prompt[:2000],
            "is_replan": is_replan
        })

    def log_planner_result(self, steps: list[dict], is_replan: bool) -> None:
        self._write("planner_result", {
            "steps": steps,
            "step_count": len(steps),
            "is_replan": is_replan
        })

    # ── Executor ──────────────────────────────────────────────────────────────
    def log_step_start(self, step: dict) -> None:
        self._write("step_start", {
            "step": step["step"],
            "tool": step["tool"],
            "description": step["description"]
        })

    def log_translator_result(self, step_num: int, tool: str, tool_input: dict) -> None:
        self._write("translator_result", {
            "step": step_num,
            "tool": tool,
            "tool_input": tool_input
        })

    def log_tool_result(self, step_num: int, tool: str, output: str, elapsed: float) -> None:
        self._write("tool_result", {
            "step": step_num,
            "tool": tool,
            "output": output[:500],
            "elapsed": round(elapsed, 3),
            "is_error": output.strip().startswith("Error:")
        })

    # ── Reflector ─────────────────────────────────────────────────────────────
    def log_reflector_verdict(self, step_num: int, verdict: dict) -> None:
        self._write("reflector_verdict", {
            "step": step_num,
            "decision": verdict["decision"],
            "reason": verdict["reason"]
        })

    # ── Replanning ────────────────────────────────────────────────────────────
    def log_replan_triggered(self, replan_count: int, reason: str, prior_outputs: list[dict]) -> None:
        self._write("replan_triggered", {
            "replan_count": replan_count,
            "reason": reason,
            "completed_steps": [
                {"step": o["step"], "tool": o["tool"]}
                for o in prior_outputs
            ]
        })

    # ── Failures ──────────────────────────────────────────────────────────────
    def log_executor_gave_up(self, replan_count: int, reason: str) -> None:
        self._write("executor_gave_up", {
            "replan_count": replan_count,
            "reason": reason
        })

    def log_unexpected_error(self, stage: str, exc: Exception) -> None:
        self._write("unexpected_error", {
            "stage": stage,
            "error_type": type(exc).__name__,
            "error_message": str(exc)
        })