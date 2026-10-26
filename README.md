# OpsAgent

**OpsAgent** is an autonomous AI‑agent framework that simulates a "AI employee" capable of fetching invoices, processing them, and entering data into a mock FinanceHub system. It demonstrates the full loop of goal identification, planning, tool execution, policy enforcement, and self‑verification.

---

##  What the project does
- **Two FastAPI services**:
  - **Sandbox (port 8001)** – mocks vendor portals and FinanceHub APIs, including realistic failures (503, duplicate entries, etc.).
  - **Dashboard (port 8000)** – UI + REST API for task submission, live SSE trace, policy approvals, and verification.
- **Autonomous agent runtime** that:
  1. Parses natural‑language tasks.
  2. Generates a step‑by‑step plan.
  3. Executes plan via HTTP calls to the sandbox.
  4. Enforces corporate policies (approval thresholds, risky domains).
  5. Verifies its own side‑effects against the SQLite store.
- **Evaluation harness** (`python -m opsagent.eval`) that runs 21 scripted scenarios and reports pass/fail rates.

---

##  Quick start (local)
### Prerequisites
- **Python 3.13** (or 3.11/3.12) – ensure `python` points to a compatible interpreter.
- **Git** – for version control.
- **Google Gemini API key** – place it in a `.env` file at the project root:
  ```
  GEMINI_API_KEY=YOUR_GEMINI_API_KEY
  ```
  (the key is never committed.)
- **Playwright browsers** (required by the sandbox PDF generator). Install with:
  ```bash
  pip install playwright
  playwright install
  ```

### Installation
```bash
# Clone the repository (if you haven't already)
git clone https://github.com/ananya-2012/OpsAgent.git
cd OpsAgent

# (Optional) create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt   # or `pip install .` if a pyproject.toml is present
```

### Running the services
```bash
# 1️⃣ Start the sandbox (mock backend) on port 8001
uvicorn opsagent.sandbox.server:app --host 0.0.0.0 --port 8001 &

# 2️⃣ Start the dashboard UI & API on port 8000
uvicorn opsagent.dashboard.app:app --host 0.0.0.0 --port 8000 &

# Verify they are up
curl http://localhost:8000/health   # → {"status":"ok","service":"dashboard",...}
curl http://localhost:8001/health   # → {"status":"ok","service":"sandbox"}
```
Open **http://localhost:8000** in a browser. You can now:
- Submit a task (e.g. `Enter the latest invoice from Acme Supplies Pvt Ltd into FinanceHub`).
- Watch the live trace as the agent reasons and calls the sandbox.
- Approve any policy prompts that appear.
- Download the generated PDF invoice from the *Evidence* tab.

### Running the evaluation harness (optional)
```bash
python -m opsagent.eval
```
It will execute the built‑in test suite and output a pass/fail summary.

---

##  Project structure
```
OpsAgent/
├─ opsagent/                   # Core package
│  ├─ dashboard/              # FastAPI UI + API
│  ├─ sandbox/                # Mock vendor & FinanceHub server
│  ├─ memory/                 # BM25 retrieval layer
│  ├─ policy/                 # Policy engine (approval thresholds)
│  ├─ runtime/                # Autonomous agent loop
│  ├─ verifier/               # Self‑verification logic
│  └─ eval/                   # Integration‑test harness
├─ .env                        # (your Gemini API key – never commit)
├─ .gitignore
├─ pyproject.toml / requirements.txt
└─ README.md (this file)
```

---

##  Extending the project
- **Add new tools** – create additional FastAPI endpoints in `opsagent/sandbox/server.py` and register them in the tool registry (`opsagent/runtime/tools.py`).
- **Change policies** – edit `opsagent/policy/policy.yaml` (e.g., adjust `APPROVAL_THRESHOLD`).
- **Swap LLM provider** – replace the Gemini client in `opsagent/runtime/agent.py` with any OpenAI‑compatible SDK.

---

##  License
This project is licensed under the MIT License.

---

##  Contact
For questions or contributions, open an issue on the GitHub repo or reach out to the author.
