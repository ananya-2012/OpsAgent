# Honest Draft Answers

## What I built in 3–5 sentences

I built a local AI employee sandbox called OpsAgent that takes a task, reads company context, uses Gemini 2.5 Flash with browser/file/API tools, and then completes work in a local FinanceHub and vendor portal environment. The project has a policy engine that blocks unsafe actions, a queue and worker for background execution, and a dashboard with live trace, approvals, and memory panels. It also includes an independent verifier that re-fetches the record after completion and flags mismatches before reporting success.

## Architecture

The app is organized around a sandbox company world, a background task worker, a Gemini runtime, and a SQLite-backed state layer. The runtime uses BM25 retrieval over docs/company_context markdown files to find company policy, then calls tools in a strict allowlist governed by a code-enforced policy engine. The dashboard shows the live trace and approval flow, while the independent verifier checks the final record against the source invoice.

## What is genuinely autonomous

The runtime is genuinely autonomous in the sense that it can choose a tool sequence from Gemini function calls, adapt after errors, and continue until the task is complete or paused for approval. It does not hard-code a fixed list of steps for each task, and it can read the sandbox, use policy-aware tools, and revise the plan as it observes failures.

## What is hard-coded

The project still depends on local sandbox endpoints, explicit tool schemas, the allowed domain list, and the threshold that triggers a human approval. Those are local design choices rather than hidden runtime magic.

## Models and tools used

The runtime uses Gemini 2.5 Flash through the google-genai SDK. It interacts with a headless browser, PDF readers, HTTP connectors, in-memory and persisted facts, and a human approval tool.

## Biggest limitation

The biggest limitation is that it is still a local sandbox demo. It is not a production-grade autonomous finance system and should not be trusted for real financial execution without a larger review and security process.

## Next two weeks

The next two weeks would focus on making the runtime more robust across ambiguous-name cases, approval flows, and verification edge cases. I would also add deeper observability, more realistic invoice variants, and stronger deployment and environment validation.
