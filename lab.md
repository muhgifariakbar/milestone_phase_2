# Hands-On Lab — Build the Model Explanation Agent

## Deliverables and schedule

Build a read-only MongoDB repository, an authenticated FastAPI service, a bounded
customer-facing explanation agent, one Dockerfile, tests, and an evaluation report.
Connect the supplied Streamlit UI. The tree and scored records are already supplied
by the organizer.

| Activity | Time |
| --- | ---: |
| Data contract, model card, and setup | 45 min |
| Guided identity and MongoDB repository | 95 min |
| Break and checkpoint | 15 min |
| Guided API and UI integration | 100 min |
| Independent explanation agent and follow-up | 115 min |
| Security, edge cases, evaluation, demo | 125 min |
| Docker packaging and grader rehearsal | 45 min |
| **Total** | **540 min** |

## Environment and project map

Python 3.11+, `venv`, FastAPI, PyMongo, Streamlit, pytest, and an instructor-approved
model provider are required. Docker with Compose is required for the packaging task.
MongoDB credentials arrive separately. There is no GPU or
training step. Use a fake collection in unit tests so most checks work without network.

```text
participant/
├── app.py, ui_contract.py, demo_personas.json   # supplied UI
├── compose.yaml, .dockerignore                  # supplied container scaffold
├── Dockerfile                                  # your single API/UI image
├── provided_model/                             # read-only tree, source, model card
├── src/
│   ├── repository.py                           # your MongoDB and data validation
│   ├── agent.py                                # your bounded explanation agent
│   └── api.py                                  # your authenticated API
└── tests/                                      # public checks; extend them
```

## Step 1 — Inspect supplied evidence (45 min, guided)

**Objective:** Separate model facts from the card-limit policy.

**Instructions:** Read `provided_model/model-card.md`, `brief.md`, and the JSON model
metadata. Identify the six features, score mapping, tier thresholds, and 36-month
balance window. Inspect a public MongoDB assessment and its monthly rows using a
read-only connection; the organizer supplies the URI. Record which fields come from the
model and which come from policy.

**Expected:** A one-page data-flow sketch: Streamlit → API/auth → agent → own MongoDB
records → validated facts → response. **Verification:** You can explain why a high
balance can coexist with a lower score. **Common error:** Asking the LLM to generate a
new score rather than explain the stored one.

## Step 2 — Implement identity-bound queries (95 min, guided)

**Objective:** Fetch only the authenticated customer's records.

**Instructions:** In `src/repository.py`, look up the bearer token in `demo_identities`.
Use the resolved `customer_id` as a parameter for all other MongoDB reads. Query
`customer_assessments` and `monthly_balances` with explicit collection names and
bounded projections. Check for exactly 36 unique months in the expected period, compute
the mean, verify model version, tier, rounding and cap, and inspect reason evidence.
Never send `customer_note` to an LLM as instructions. Do not implement database writes.

**Expected:** Repository methods return a validated own assessment or an unavailable
result. **Verification:** Token A cannot retrieve customer B by adding B's ID to a
question or JSON payload. **Common errors:** Trusting UI-selected IDs, using the LLM's
tool argument as an ID, or treating a stored `status` value as proof of integrity.

> **Checkpoint:** An invalid token fails with 401, and incomplete or inconsistent records
never produce a fabricated limit.

## Step 3 — Build the API and connect the UI (100 min, guided)

**Objective:** Meet the fixed contract in `brief.md`.

**Instructions:** Complete `src/api.py`. Keep `/healthz` public. Add the two protected
routes with safe 401, 409, and 503 responses. Run `uvicorn src.api:app --reload`, then
`streamlit run app.py` in another terminal. Select two named personas and confirm the
score panel comes from your API. Switching personas must clear the old chat history.

**Expected:** Each persona receives only their own score and limit. **Verification:**
Stop the API and confirm Streamlit shows an error without displaying stale facts.
**Common errors:** Giving Streamlit MongoDB credentials or hard-coding scores in the UI.

## Step 4 — Implement the explanation agent (115 min, independent)

**Objective:** Answer questions from verified records and handle follow-up.

**Instructions:** Give the model only bounded, read-only tool choices for own assessment,
own balance summary, and refusal. Limit history to six turns and validate each tool
call. Format score, arithmetic, units, date, and reason evidence in trusted code. The
LLM may choose the topic or conversational framing; it must not invent values or
override identity. If reason evidence is missing, give the verified score if available
but abstain from a causal or model-path explanation.

**Expected:** "Why this limit?" identifies the actual 36-month mean, score tier,
multiplier, rounding, and cap. **Verification:** Compare the answer with MongoDB and the
policy table. **Common errors:** Calling a tree path a cause, promising a future score,
or accepting stored text as instructions.

## Step 5 — Evaluate announced challenge categories (125 min, independent)

**Objective:** Demonstrate robust behavior before the organizer introduces exact cases.

**Instructions:** Add tests and a 12-case report covering factual answers, follow-ups,
unavailable history, score/balance contrast, rounding/cap, missing reasons, stale or
contradictory records, cross-customer access, stored prompt injection, and MongoDB or
provider failure. For each case record input, expected behavior, actual response,
outcome, and pass/fail. Include a short note about the synthetic model's limits.

**Expected:** Passing tests, a reproducible report, and a 5–7 minute demo. **Verification:**
The instructor may upload new customer records and use the same public UI contract or
direct API calls without changing your code. **Common errors:** Testing only ordinary
customers or relying on UI behavior as the security boundary.

## Step 6 — Package and rehearse with Docker (45 min, independent)

**Objective:** Make the API and UI reproducible on the grader machine.

**Instructions:** Write one `Dockerfile` at the participant root. Use a Python 3.11+
Linux base image, install `requirements.txt`, and copy the runtime application files.
The provided `compose.yaml` starts two services from that image and injects settings
at runtime. Do not include `.env`, API keys, a local `.venv`, or MongoDB data in the
image. The organizer supplies an external read-only MongoDB connection. Copy
`.env.example` to an untracked `.env`, then run:

```powershell
docker compose config --quiet
docker compose up --build -d
curl.exe http://localhost:8000/healthz
```

Open `http://localhost:8501`, select a persona, and confirm that the UI reaches the
API at `http://api:8000` inside Compose. Use `docker compose logs api ui` to debug
and `docker compose down` to clean up. **Expected:** Both services start from the
same image and the persona assessment comes from the API. **Common errors:** Using
`localhost` as the UI's API hostname inside its container, binding services only to
`127.0.0.1`, or copying `.env` into the image. A packaging failure loses rubric
points but is not by itself an automatic milestone failure.

## Debugging and extensions

| Symptom | Likely cause | Action |
| --- | --- | --- |
| 401 for every request | Token lookup or bearer parsing incorrect | Check `demo_identities` query and header parsing |
| 409 for ordinary persona | Missing rows or wrong model-version/policy check | Count months and compare the supplied card |
| MongoDB timeout | URI, network, or read-only role issue | Verify organizer URI outside source code |
| Wrong limit | Averaging wrong grain or rounding upward | Use 36 closing balances and published policy |
| Other customer's facts | Client or LLM ID used in query | Bind ID from token lookup only |
| Prompt injection succeeds | Stored note treated as instruction | Exclude note from tool instructions and answer facts |
| UI container cannot reach API | Container uses `localhost:8000` | Use Compose service name `api` in `BANK_API_URL` |
| Container exits on startup | App files or dependencies missing | Inspect `docker compose logs api ui` and Dockerfile copy steps |

**Stretch:** Add a structured record-review request proposal without writing to MongoDB;
add latency and error counters without logging raw customer messages. Submit your code,
tests, architecture sketch, evaluation report, and demo notes. Do not submit credentials
or real customer data. See `rubric.md` for scoring.
