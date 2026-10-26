# Demo Script

## 3-minute local demo

### 1. Prepare the environment

```bash
cd /Users/ananyapandiri/CentrAlign
python3 -m pip install -e .
python3 -m playwright install chromium
```

### 2. Start the sandbox

```bash
DEMO_MODE=false GEMINI_API_KEY="$GEMINI_API_KEY" python3 -m uvicorn opsagent.sandbox.server:app --host 0.0.0.0 --port 8001
```

### 3. Start the dashboard

```bash
DEMO_MODE=false GEMINI_API_KEY="$GEMINI_API_KEY" python3 -m uvicorn opsagent.dashboard.app:app --host 0.0.0.0 --port 8000
```

### 4. Open the dashboard

Visit http://localhost:8000.

### 5. Submit a task

Enter:

Enter the latest invoice from Acme Supplies Pvt Ltd into FinanceHub

### 6. Show the live trace

Explain the steps while the trace streams: understand context, inspect vendor names, validate date format, submit to FinanceHub, and verify.

### 7. Trigger a failure and recover

Use a high-value amount or an ambiguous vendor query to force a human approval or clarification. Then show the UI and explain how the task pauses and resumes.

Example failure:

Enter the latest invoice from Acme for Rs 75000 into FinanceHub.

Expected result: the task pauses for approval or asks for clarification because the vendor is ambiguous and the write exceeds threshold.

### 8. Review the verification

Open the completed task and confirm the verification report matches the source invoice exactly.

## Recovery flow

If the agent loops or fails, reset the sandbox and rerun:

```bash
curl -X POST http://localhost:8001/api/reset
```

Then re-submit the task and explain how the runtime uses its audit log and policy decisions to adapt.
