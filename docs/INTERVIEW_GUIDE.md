# Interview Guide

## Module walkthrough

### 1. Configuration

The project settings live in opsagent/config.py and include the model, demo mode, ports, credential variables, and approval threshold.

### 2. Runtime loop

The main autonomous loop is in opsagent/runtime/agent.py. It loads company context, calls Gemini with tool declarations, checks policy, executes the tool, and feeds the result back into the conversation.

### 3. Policy engine

The policy engine in opsagent/policy/engine.py is the guardrail before every tool call. It checks domain, risk, approval threshold, and prompt injection patterns.

### 4. SQLite state

The database layer in opsagent/database.py stores tasks, approvals, audit entries, queue state, and persistent facts.

### 5. Sandbox company world

The sandbox server in opsagent/sandbox/server.py runs the vendor portal and FinanceHub. It includes login, session expiry, pagination, invoice data, and validation rules.

### 6. Dashboard

The dashboard app in opsagent/dashboard/app.py presents the live trace and approval workflow.

### 7. Verifier

The independent verifier in opsagent/verifier/verify.py re-fetches the FinanceHub record and compares it against the source invoice.

## Likely interview questions with answers

1. Q: Why did you use SQLite for this project? A: It keeps the design simple, inspectable, and local for a demo while still supporting tasks, approvals, and audit logs.
2. Q: Why is all page content treated as untrusted? A: Because prompt injection and malicious instructions can appear in content that is not the system prompt.
3. Q: What happens if a vendor name is ambiguous? A: The runtime is expected to ask a human for clarification instead of guessing.
4. Q: How does the approval workflow work? A: The policy engine triggers a pending approval request when a write action exceeds the threshold or when a forbidden action is attempted.
5. Q: What is the purpose of BM25 retrieval? A: It finds the most relevant company context chunks from the markdown documents.
6. Q: Why does the project have an independent verifier? A: To avoid trusting the agent’s own final statement.
7. Q: What is the sandbox for? A: It creates a safe local environment with realistic validation rules and behaviour without real finance systems.
8. Q: Why are delete operations blocked? A: Because the project policy explicitly forbids destructive action.
9. Q: What happens if the first FinanceHub submission fails with 503? A: The server injects a one-time transient failure and the agent must retry.
10. Q: What is the session expiry behavior? A: The vendor portal session expires after a short time and the agent must re-login.
11. Q: How is the task queue durable? A: It uses SQLite-backed queue entries and resumption logic.
12. Q: Why use FastAPI? A: It is a lightweight framework with good API and dashboard support.
13. Q: Why use Playwright? A: It allows browser automation for login, invoice list navigation, and form interactions.
14. Q: What does the dashboard show? A: It shows new tasks, running state, live SSE trace, policies, memory, approvals, and verification results.
15. Q: What is DEMO_MODE for? A: It limits task throughput to protect the Gemini API key and keep the demo under control.
16. Q: What is the approval threshold? A: Rs 50,000.
17. Q: Why is the company context not hard-coded into the runtime? A: To keep the task knowledge in files and allow the system to adapt via retrieval.
18. Q: What is a policy gate? A: A code-level decision before the tool executes, not just an instruction in the prompt.
19. Q: What is the biggest risk in an LLM-driven workflow? A: Bad tool choices and prompt injection.
20. Q: What is the verification loop’s purpose? A: It ensures the record in FinanceHub matches the source invoice.
21. Q: Why do invoices have different layouts and formats? A: To force the agent to read the document, not just rely on a single fixed format.
22. Q: Why does the code treat all PDF content as data? A: Because a PDF can contain text that looks like instructions but must not be executed.
23. Q: What is the effect of a denied approval? A: The task pauses and the workflow stops until a human decision is made.
24. Q: Why is there a human-in-the-loop requirement? A: Some actions can be irreversible or exceed policy thresholds.
25. Q: What remains for production? A: More security review, deployment hardening, and operator tooling.

## Five live-modification exercises

1. Change the threshold in the YAML or config and explain the impact on approval flow.
2. Add a new vendor and invoice type to the sandbox and verify the retrieval layer picks it up.
3. Change the allowed domain list and watch the policy engine reject the call before it runs.
4. Trigger a 503 on the first submission and ask the runtime to retry without manual intervention.
5. Add a new dashboard section to show policy decisions in a more readable format and confirm the SSE stream still updates.
