from pathlib import Path
import anthropic
from dotenv import load_dotenv

load_dotenv()

# -----------------------------------------------
# PATHS
# -----------------------------------------------
WORKSPACE_PATH = Path(__file__).parent /'workspace'
TRACES_PATH = Path(__file__).parent /'outputs'/'traces.jsonl'
EVAL_RESULTS_PATH = Path(__file__).parent /'outputs'/'eval_results.jsonl'

# -----------------------------------------------
# MODEL
# -----------------------------------------------
CLIENT = anthropic.Anthropic(timeout=60)
MODEL_NAME = 'claude-sonnet-4-6'

# -----------------------------------------------
# EXECUTOR
# -----------------------------------------------
MAX_REPLANS = 3