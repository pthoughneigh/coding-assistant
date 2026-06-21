# Coding Assistant Agent

A planner → executor → reflector agent that fixes bugs in a small Python codebase using four tools: `read_file`, `write_file`, `search_code`, and `run_tests`. Built as a Phase 3 capstone project, with full tracing, structured logging, and an automated eval harness.

## What it does

Given a natural-language question like *"Fix the bug in task_manager.py"*, the agent:

1. **Plans** a sequence of tool calls (`planner.py`)
2. **Executes** each step, translating the step's intent into concrete tool arguments via an LLM call (`executor.py`, `step_translator`)
3. **Reflects** on each tool result, deciding whether to continue or replan (`reflector.py`)
4. **Replans** when a step fails or produces an unsatisfactory result, picking up from where execution left off rather than starting over

The agent will give up gracefully (raising a clear error) if it determines there's nothing to fix — for example, if a referenced file doesn't exist anywhere in the workspace.

## Folder structure

```
coding_assistant/
├── agent/
│   ├── agent.py          # Top-level entry point: runs planner → executor
│   ├── planner.py        # Generates the initial step-by-step plan
│   ├── executor.py       # Runs each step, dispatches tools, triggers replans
│   ├── reflector.py      # Judges each step's result, decides continue/replan
│   ├── prompts.py        # All system prompts (planner, step translator, reflector)
│   └── tools.py          # The four tools: read_file, write_file, search_code, run_tests
├── evals/
│   ├── fixtures/
│   │   ├── task_manager_buggy.py     # Starting code for q1-q4 (filter bug)
│   │   └── task_manager_correct.py   # Starting code for q5 (regression-detection test)
│   ├── cases.py           # Eval case definitions
│   └── harness.py         # Runs cases, checks outcomes, writes results
├── observability/
│   ├── tracer.py          # Structured JSONL event logging (one line per event)
│   └── logger.py          # Colorized human-readable console output
├── outputs/
│   ├── traces.jsonl       # Append-only trace log, one record per agent/planner/reflector event
│   └── eval_results.jsonl # Append-only eval results log
├── workspace/
│   ├── task_manager.py        # The file the agent actually reads/edits during a run
│   └── test_task_manager.py   # The test suite the agent and the harness both run
├── config.py               # Paths, model name, MAX_REPLANS
├── main.py                 # Interactive CLI entry point
└── requirements.txt
```

`workspace/task_manager.py` is the live file the agent edits. The eval harness overwrites it with a fixture's `starting_code` before every case, so each case starts from a known, reproducible state.

## Setup

```bash
pip install -r requirements.txt
```

Requires a `.env` file in the project root with an Anthropic API key:

```
ANTHROPIC_API_KEY=sk-...
```

(`config.py` loads this via `python-dotenv`.)

## Running it

**Interactive CLI** — ask the agent questions directly:

```bash
python main.py
```

Type a question (e.g. `Fix the bug in task_manager.py`), or `QUIT` to exit.

**Eval suite** — run all defined cases and get a pass/fail report:

```bash
python -m evals.harness
```

Results are printed to the console and appended to `outputs/eval_results.jsonl`. Trace events for every run are appended to `outputs/traces.jsonl`, keyed by a per-run `run_id`.

## Architecture

### The planner → executor → reflector loop

```
question
   │
   ▼
planner ──────► [step 1, step 2, step 3, ...]
   │
   ▼
executor loop:
   for each step:
     step_translator(step) ──► concrete tool arguments
     run_tool(step, arguments) ──► result
     reflector(result) ──► {decision: continue | replan, reason}
     if replan:
       planner(question + reason + completed steps) ──► new remaining steps
       (restart loop with new steps, replan_count += 1)
       if replan_count > MAX_REPLANS: give up, raise RuntimeError
   │
   ▼
final result
```

Each of `planner`, `step_translator`, and `reflector` is a separate LLM call with its own system prompt (all defined in `prompts.py`). This separation of concerns means each call has one narrow job and a focused prompt, rather than one large prompt trying to do everything at once.

### The four tools

| Tool | Purpose | Input |
|---|---|---|
| `read_file` | Read a file's contents | `file_name` |
| `write_file` | Overwrite a file with new content | `file_name`, `file_content` |
| `search_code` | Grep-style search across the whole workspace | `pattern` |
| `run_tests` | Run pytest on a test file | `file_name` |

All four are sandboxed to `WORKSPACE_PATH` — any path that resolves outside the workspace directory is rejected. All four catch their own exceptions internally and return `"Error: ..."` strings rather than raising, so the agent (and the reflector) can reason about failures as plain text rather than handling exceptions.

### Observability

Two parallel logging systems serve different purposes:

- **`logger.py`** — colorized, human-readable console output. One color per agent component (planner, executor, step translator, reflector), truncated previews of long content. Meant for watching a run live.
- **`tracer.py`** — structured JSONL, one event per line, written to `outputs/traces.jsonl`. Every agent/planner/executor/reflector event is recorded with a timestamp, `run_id`, event name, and payload. Meant for after-the-fact analysis — the eval harness reads this file back to count how many replans occurred in a given run.

The two systems log independently and don't share truncation limits; the tracer's payloads are capped (e.g. tool output truncated to 500 chars) for log-file size, while the data actually used by the LLM calls themselves (in `prior_outputs`) is not capped at the same point.

## The eval harness

`evals/cases.py` defines five cases, each exercising a different part of the agent's behavior:

| Case | Tests | Expected outcome |
|---|---|---|
| q1 | Straightforward bug fix, file name given | Agent fixes it, tests pass |
| q2 | Same bug, vaguer question phrasing | Agent fixes it, tests pass |
| q3 | Bug fix where the file name in the question is wrong | Agent searches, finds the real file, fixes it |
| q4 | A file that doesn't exist anywhere | Agent searches, fails to find it, gives up correctly (raises, doesn't hallucinate a fix) |
| q5 | A feature request whose naive implementation breaks existing tests | Agent must detect the regression via the reflector and arrive at a non-obvious correct fix |

For each case, `run_case` resets `workspace/task_manager.py` to the case's `starting_code`, runs the agent, and then **independently re-runs pytest itself** — it does not trust the agent's own internal `run_tests` call or the reflector's verdict, since either could be wrong. This independent check is what actually decides pass/fail for cases expecting success.

q4 is the only case expecting the agent to *fail* in a specific way (a `RuntimeError` containing `"Replanner returned an empty step list"`), confirming the agent recognizes a dead end rather than fabricating a fix.

q5 is intentionally the hardest case. The straightforward reading of "add a timestamp to the task title" is to append the timestamp directly to the `title` string — which breaks three existing tests that check exact title equality. The correct fix is to add a separate `created_at` field to the `Task` dataclass (via `dataclasses.field(default_factory=datetime.now)`), leaving `title` untouched. The agent has to discover this through the replan loop, not because it was told the answer.

## Key design decisions

### Reflecting on every step, including `run_tests`

Early in development, the reflector skipped `run_tests` steps entirely — the executor would run the test suite, log the result, and move on regardless of whether tests passed. This meant a step could fail its own verification and the agent would still return a "successful" answer. Fixed by removing the tool-specific exclusion so every step, including `run_tests`, goes through the reflector.

### Reflector visibility into `write_file` content

The reflector originally only ever saw `write_file`'s success message (`"Successfully wrote 'x.py'"`) — never the actual code that was written. When a later step needed to be judged against "did the previous fix actually work," the only file content available in `prior_outputs` was a stale snapshot from an earlier `read_file` call, sometimes from *before* the real fix was written. Fixed by enriching the `write_file` entry in `prior_outputs` with the actual `file_content` that was written (captured from `arguments['file_content']` at the moment of the call), so later reflector and step-translator calls see ground truth, not stale state.

### Test files are off-limits to the planner

Without an explicit rule, the planner would sometimes "fix" a failing test by editing the test file itself to match a broken implementation, rather than fixing the implementation. Two independent guardrails now prevent this:

- `PLANNER_PROMPT` explicitly forbids generating a `write_file` step against any `test_*.py` file or the file `run_tests` checks.
- `REFLECTOR_PROMPT` independently flags it as a replan-worthy problem if a `write_file` step ever targets a test file, as a second line of defense in case the planner rule is bypassed.

### The reflector occasionally relitigated a correct fix — and why that needed a code-level fix, not a better prompt

q5 exposed a subtle, low-frequency failure: after the agent correctly reverted `task.title` to leave it untouched (relying on `created_at` for the timestamp) and `run_tests` showed all 9 tests passing, the reflector would sometimes still return `replan`, reasoning that the fix "didn't literally add a timestamp to the title" — taking the user's wording too literally even though the fix was functionally correct.

Three rounds of prompt engineering each reduced but did not eliminate this:
1. A narrow rule scoped to `write_file`/`run_tests` outputs specifically — still failed when the bad reasoning surfaced on a `read_file` step instead.
2. A general, tool-agnostic rule — reduced failure rate further, but the model would occasionally ignore the instruction outright.
3. Restructuring the reflector's user message to frame the original question as background context rather than something to directly compare against the result — the model sometimes directly contradicted this framing in its own stated reasoning.

The eventual fix was to stop asking the LLM a question that didn't need to be asked: pytest's pass/fail verdict is an externally-decided fact, not a matter of interpretation. `executor.py` now checks, in plain Python, whether a `run_tests` step's result cleanly says `"Result: passed"` *and* whether any `write_file` step in the run has touched a test file (via a small helper, `test_file_was_written`). If both conditions hold, the result is auto-accepted without ever calling the reflector LLM for that step — removing the one specific decision point where prompt wording had proven unreliable. Across repeated isolated test runs, this took q5's pass rate from roughly 2/5 (pre-fix) to 5/5 (post-fix), with consistently lower replan counts.

This is the general principle the fix follows: **if a fact is externally verifiable, check it in code; reserve LLM judgment for things that are genuinely matters of interpretation** (is this search broad enough, does this file content look reasonable, is this the right file to read next). The reflector still makes every other judgment call in the loop — this fix didn't remove judgment from the system, it removed judgment from the one place that didn't need it.

## Known limitations

- `MAX_REPLANS` (currently 3, in `config.py`) is a hard ceiling. A case that legitimately needs more than 3 replan cycles to resolve will fail even if it's making genuine progress.
- The mechanical `run_tests` shortcut trusts that the test file hasn't been tampered with. This is enforced by the planner/reflector rules described above, which are themselves prompt-based and not 100% guaranteed — if those rules were ever bypassed, the shortcut would have no independent way to detect a weakened test suite.
- The agent operates on a single hardcoded workspace with one implementation file and one test file. It has no concept of multi-file projects, imports between modules, or running a subset of tests.
- Eval cases are run sequentially against a real LLM, so results have some run-to-run variance (see q5's design decision above) — the harness does not currently support running a case N times and aggregating pass rate automatically; that was done manually during development by invoking `evals.harness` with a single case isolated in `cases.py`.