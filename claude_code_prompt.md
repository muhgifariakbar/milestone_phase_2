Read README.md first, then brief.md, lab.md, rubric.md and submission-checklist.md in this folder. Then read everything in /example (the three notebooks). Treat those notebooks as the reference for how I should build the milestone: the README is the task, /example is the style and pattern guide.

Goal: complete the milestone described in README.md so it scores well against rubric.md, without tripping any hard gate.

What to build
1. src/repository.py: read only MongoDB access. Resolve the bearer token through demo_identities, then bind every other query to the resolved customer_id. Validate exactly 36 unique months from Jan 2023 to Dec 2025, the mean balance, model version, tier, rounding down to IDR 100,000, the IDR 100 million cap, and reason evidence. Return a validated result or an unavailable result. Never send customer_note to the model as instructions.
2. src/agent.py: a bounded router with three tools only (own assessment, own balance summary, refusal). Max six history turns. Stop after one validated tool choice. Reject unknown tools and arguments. The model may choose a topic, never a customer ID. Numbers, arithmetic, dates and reasons are rendered by trusted code, not by the LLM. Handle provider failure and invalid output safely. Keep the router signature compatible with tests/test_public_contract.py (route returns a tool name and an args dict).
3. src/api.py: GET /healthz, GET /api/v1/me/assessment, POST /api/v1/chat, with the 401, 409 and 503 behavior from the brief. No internal error text in responses. Keep create_app(database, router) injectable for tests.
4. Dockerfile: one image for both api and ui services in compose.yaml. Python 3.11+ Linux base, install requirements.txt, copy runtime files only, no .env, .venv or credentials.
5. Tests: extend tests/ with a fake MongoDB so everything runs offline. Cover all eight edge case categories in README.md, plus cross customer access, stored prompt injection, and database or provider failure.
6. Docs: an evaluation report with at least 12 cases (input, expected, actual, pass/fail), a short architecture note with production limits, setup and run commands, and 5 to 7 minute demo notes. Also answer the six questions in assessment.md briefly.

How to use /example
Follow the patterns the notebooks teach: tool functions that do the exact computation in code, the model only chooses or frames, a read only guardrail before touching the database, grounded answers built from retrieved rows, an honest answer on empty results, and .env loading for secrets. Do not copy the open ended loop from create_agent, because the brief requires one validated tool choice.

Rules
- Do not edit or retrain anything in provided_model/. Do not edit app.py, ui_contract.py, demo_personas.json or compose.yaml.
- No database writes anywhere. No credentials in code. Do not commit or push.
- Do not ask me for the MongoDB URI or API key. Use the fake database for tests, and verify Docker with `docker compose config --quiet` and a build only.
- Before you install, add or use anything outside requirements.txt (for example langchain, langchain-openai or python-dotenv, which the notebooks use), STOP and tell me the exact package and version, why you want it instead of the already listed openai SDK, and what it adds to requirements.txt and the Docker image. Wait for my approval. If I say no, use the openai SDK directly.
- If the README and the notebooks disagree, the README wins. Tell me about the conflict.

Process
Start with a short plan and the file list you will touch. Work in small steps and run `python -m pytest -q` after each one. Finish with a summary of what passes, what is untested because there is no live Mongo or API key, and any assumptions you made.


