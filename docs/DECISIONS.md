# Key Decisions and Assumptions

## 1. Local-only sandbox

The project intentionally keeps all business flows inside local FastAPI endpoints and generated PDF invoices. This reduces risk, keeps the demo reproducible, and avoids connecting to real vendor or finance systems.

## 2. Policy enforcement in code

A policy check happens before every tool call. This is stronger than simply adding rules to the prompt. The engine checks domain allowlists, risk level, approval thresholds, and injection patterns.

## 3. Human approval is an explicit part of the action loop

When a transaction exceeds Rs 50,000 or a denial of access is required, the runtime pauses and creates an approval request. The task does not continue until the human responds.

## 4. Company knowledge is kept in docs

Task knowledge is intentionally limited to the markdown files in docs/company_context and the persistent fact table. This keeps the design aligned with the requirement that no hidden task logic be encoded in the runtime.

## 5. Verification is independent

The verifier re-fetches the FinanceHub record and compares it against the source invoice instead of trusting the model or the runtime state. This prevents false completion claims.

## 6. Demo mode is a safety guard

The demo mode rate limiter protects the Gemini API key and keeps the local demo from running uncontrolled. The project must be run with DEMO_MODE=false for a full real evaluation run.

## 7. Untrusted content policy

The runtime treats page text, PDF text, and API payloads as data. It does not execute instructions embedded in those sources.

## 8. Use of SQLite for a simple local task system

SQLite is sufficient for tasks, approvals, audit log, and queueing in a single-workspace demo. It is easy to inspect during interviews and keeps the project local.
