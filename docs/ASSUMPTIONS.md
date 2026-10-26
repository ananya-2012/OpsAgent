# Assumptions and Runtime Decisions

- The project is intended to run locally with a valid Gemini API key loaded from `.env`.
- The active runtime model is `gemini-flash-lite-latest`, which is a supported Google GenAI alias that passes the live function-calling and latency checks used in this environment.
- Local sandbox services on `localhost` are the only allowed external domains for tool execution.
- Human approval is required for actions above the configured threshold in `opsagent/config.py`.
- The dashboard and sandbox are run as separate local services, and the evaluator orchestrates them for end-to-end verification.
- All tool outputs and documents are treated as untrusted data until validated by policy and the independent verifier.
