from pathlib import Path

# -----------------------------------------------
# PATHS
# -----------------------------------------------
WORKSPACE_PATH = Path(__file__).parent /'workspace'
TRACES_PATH = Path(__file__).parent /'outputs'/'traces.jsonl'
EVAL_RESULTS_PATH = Path(__file__).parent /'outputs'/'eval_results.jsonl'

# -----------------------------------------------
# MODEL
# -----------------------------------------------
MODEL_NAME = 'claude-sonnet-4-6'

# -----------------------------------------------
# EXECUTOR
# -----------------------------------------------
MAX_REPLANS = 3