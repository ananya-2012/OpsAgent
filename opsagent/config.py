"""Central configuration for OpsAgent."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
COMPANY_CONTEXT_DIR = DOCS_DIR / "company_context"
POLICY_FILE = PROJECT_ROOT / "opsagent" / "policy" / "policy.yaml"
DB_PATH = PROJECT_ROOT / "data" / "opsagent.db"

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# LLM Config
LLM_MODEL = "gemini-2.5-flash"
LLM_MAX_TOKENS = 8192
LLM_TEMPERATURE = 0.2

# Runtime
MAX_STEPS_PER_TASK = 50
STEP_TIMEOUT_SECONDS = 120
STALL_DETECTION_WINDOW = 5  # consecutive similar actions = stall
LOOP_DETECTION_HASH_WINDOW = 8  # check last N action hashes for loops

# Demo mode
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
DEMO_MAX_TASKS_PER_HOUR = int(os.getenv("DEMO_MAX_TASKS_PER_HOUR", "10"))

# Sandbox
SANDBOX_PORT = int(os.getenv("SANDBOX_PORT", "8001"))
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8000"))
SANDBOX_BASE_URL = os.getenv("SANDBOX_BASE_URL", f"http://localhost:{SANDBOX_PORT}")

# Sandbox credentials (from env, never hardcoded in business logic)
SANDBOX_USERNAME = os.getenv("SANDBOX_USERNAME", "ops_user")
SANDBOX_PASSWORD = os.getenv("SANDBOX_PASSWORD", "sandbox_pass_2024")

# Retry config
RETRY_MAX_ATTEMPTS = 3
RETRY_BASE_DELAY = 1.0
RETRY_MAX_DELAY = 30.0

# Approval threshold (INR)
APPROVAL_THRESHOLD = 50000.0
