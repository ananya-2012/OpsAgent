# Next Steps (2-week plan)

## Week 1: Harden the runtime

- Add stronger task-state transitions and resumability checks.
- Improve the tool policy checks to parse more amount fields and action names.
- Add end-to-end tests for login expiry, high-value approval flow, and ambiguous vendor resolution.
- Improve the audit log formatting and visual presentation in the dashboard.

## Week 2: Improve realism and ops quality

- Add more realistic invoice layouts and negative test cases.
- Expand the verifier to compare dates, vendor IDs, amounts, status, and invoice numbers with explicit detail.
- Add a richer memory summarization layer and cross-task fact deduplication.
- Create a production-quality deployment workflow with environment validation and health checks.
- Record an interview-ready walkthrough and refine the demo script for live demos.

## Immediate follow-up items

- Tune the Gemini tool-calling prompts to maximize successful task completion on local sandbox tasks.
- Add a non-blocking telemetry layer for metrics on retry rates, policy blocks, and verification failures.
- Review which scenarios pass reliably and which still require user approval or clarification.
