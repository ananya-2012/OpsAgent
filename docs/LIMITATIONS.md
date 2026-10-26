# Honest Limitations

This project is deliberately scoped to a local sandbox and cannot claim to be a production-grade autonomous finance platform.

## Hard-coded or implicit assumptions

- Localhost and 127.0.0.1 are the only permitted external domains.
- Sandbox usernames and passwords default to ops_user / sandbox_pass_2024 if env variables are absent.
- The default demo budget is limited to one hour of tasks in DEMO_MODE.
- The project depends on the Google GenAI SDK and a valid Gemini API key for the runtime to complete autonomous tasks.
- Browser automation uses a single headless Chromium context and is not designed for multi-user concurrency.
- The sandbox does not support real bank integrations or actual legal approval flows.
- The vendor lookup and invoice data are synthetic and generated in memory for the local environment.

## What is intentionally not claimed

- No claim is made that the system is safe for production financial processing.
- No claim is made that the model will always choose the right next step without human oversight.
- No claim is made that the LLM never misreads ambiguous naming or invoice content.
- No claim is made that prompt-injection filtering is perfect; it is a practical local guardrail, not a security guarantee.

## Specific local constraints

- The dashboard and sandbox are intended for local development and demos.
- Only the code in this repository and the local sandbox are in scope.
- Render.yaml is a deployment blueprint only; it does not connect to a real external system unless the user configures it.
- The task knowledge is intentionally limited to the company context markdown files and the persistent facts store.

## This project is intentionally honest about risk

Any shortcut, hidden setting, or hard-coded assumption is documented here instead of being hidden in the prompt or the app logic.
