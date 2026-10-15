# Submission Checklist

- [ ] `src/repository.py`, `src/agent.py`, and `src/api.py` are complete.
- [ ] One participant-written `Dockerfile` builds an image used by both services in the supplied `compose.yaml`.
- [ ] `docker compose up --build -d` starts API and UI; `/healthz` and the Streamlit page respond.
- [ ] No credentials, `.env`, `.venv`, or local bind mount is required in the image.
- [ ] The supplied `app.py` connects to the participant API and changes demo personas.
- [ ] MongoDB URI and LLM key come from environment variables, never source code.
- [ ] Backend identity binds every MongoDB query; no client or LLM customer ID is trusted.
- [ ] Score, limit, date, and model-path reasons come from validated stored records.
- [ ] Missing, stale, inconsistent, or unavailable data produces an honest response.
- [ ] All eight announced edge-case categories in `README.md` have test coverage.
- [ ] Evaluation report has at least 12 cases with expected, actual, and pass/fail.
- [ ] README or demo notes show setup, test, API, and UI commands plus limitations.
- [ ] Submission includes `Dockerfile`, `compose.yaml`, and `.dockerignore` for the grader.
- [ ] No real customer data, MongoDB credentials, `.env`, or API keys are submitted.
