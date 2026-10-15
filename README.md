# Phase 2 Milestone — Explain a Bank Model to Its Customer

Versi Bahasa Indonesia dengan format milestone lengkap: [README-id.md](README-id.md).

You are building a **customer-facing explanation agent** for a fictional bank. The
organizer has already generated the banking histories, trained the tree model, scored
the customers, and set the card-limit policy. **You do not train or change the model.**
Your job is to connect a read-only MongoDB dataset to an authenticated API and explain
the recorded score and limit accurately through the supplied Streamlit app.

**Level:** Intermediate · **Time:** Three mentoring sessions of 180 minutes, plus a
5–7 minute demo · **Main deliverable:** working agent API, one Dockerfile, tests,
evaluation report, and architecture note.

Read [brief.md](brief.md), [lab.md](lab.md), [rubric.md](rubric.md), and
[submission-checklist.md](submission-checklist.md). The supplied [model card](provided_model/model-card.md),
`provided_model/model.json`, evaluation report, and training source are reference
materials. Do not edit or retrain them. The organizer uploads scored records to MongoDB
and supplies a read-only URI separately.

## Your work

Complete `src/repository.py`, `src/agent.py`, and `src/api.py`. The provided `app.py`,
`ui_contract.py`, and `demo_personas.json` are the customer UI and its public personas.
The UI calls only your API; it never reads MongoDB or the model artifact directly.
Write one `Dockerfile` that builds a Linux image for both services in the supplied
`compose.yaml`. MongoDB is external and is not part of Compose.

Your API must implement:

| Method | Path | Result |
| --- | --- | --- |
| GET | `/healthz` | `{"status":"ok"}` |
| GET | `/api/v1/me/assessment` | Own stored score, limit, balance basis, model version, and verified reason evidence |
| POST | `/api/v1/chat` | `{"answer":"...","outcome":"answered|refused|unavailable"}` |

The last two routes require `Authorization: Bearer <demo-token>`. Resolve the identity on
the backend through MongoDB. Do not take a customer ID from the browser, request JSON,
LLM tool arguments, or chat history as authorization. An invalid token returns 401;
an unavailable or inconsistent assessment returns 409 on the assessment route and an
`unavailable` chat answer. Keep all MongoDB access read-only.

## Announced edge-case categories

The organizer may introduce **new fictional customers and prompts just before grading**.
The exact identities and expected responses are withheld until then, but every category
you may encounter is listed here:

1. **Incomplete history:** Fewer than 36 unique monthly balances, or a missing month in
   the January 2023–December 2025 window. Do not estimate a score or limit.
2. **Score versus balance:** A high balance may accompany a lower score, and a strong
   score may accompany a modest limit. Explain the model score and balance multiplier as
   distinct steps.
3. **Limit arithmetic:** A value may require rounding down to IDR 100,000 or hit the
   IDR 100 million cap. Show the actual tier and formula, not an LLM calculation.
4. **Missing or inconsistent reason evidence:** A score may exist without usable
   model-path reasons. You may show a verified score, but abstain from explaining its
   drivers and offer record review.
5. **Stale model version or conflicting data:** An assessment may disagree with the
   supplied model version, balance average, tier, or limit policy. Do not silently repair
   it or present the contradiction as fact.
6. **Another customer's data:** A request or follow-up may name a different customer.
   Refuse access even if that customer exists in MongoDB.
7. **Prompt injection in stored text:** `customer_note` is untrusted data. Never follow
   instructions found there or expose unrelated records, prompts, or secrets.
8. **Database or model-provider failure:** Return a safe, explicit unavailable response.
   Never fabricate a score, reason, or limit.

The model-path reasons are **associations in this fitted tree**, not causal claims or
promises about future scores. This entire case is synthetic classroom material and must
not be presented as a real bank policy or a real lending decision.

## Start

Use Python 3.11+ and a read-only MongoDB URI from the organizer:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:MONGODB_URI = "your-read-only-uri"
$env:MONGODB_DATABASE = "bank_milestone"
$env:OPENAI_API_KEY = "instructor-provided-key"
$env:OPENAI_MODEL = "instructor-selected-model"
python -m pytest -q
uvicorn src.api:app --reload
```

On macOS/Linux, activate with `source .venv/bin/activate` and use `export` for environment
variables. In a second terminal, run `streamlit run app.py`. The public tests are expected
to fail on unimplemented API routes until you complete them. Never commit a real URI or
API key. Use `DEMO_PERSONAS_PATH` only when the organizer supplies an additional catalog
for a grading session.

### Docker delivery

The organizer supplies `compose.yaml` and `.dockerignore`; you write `Dockerfile`.
Use the same image for the API and UI. Install `requirements.txt` inside it and copy
the runtime app files. The build must not depend on a local `.venv`, bind mount, or
credentials. Compose injects the read-only MongoDB URI and provider settings at
runtime and sets `BANK_API_URL=http://api:8000` for the UI.

Copy `.env.example` to a local `.env`, fill in the organizer-provided values, and keep
that file out of Git. From `participant/` run:

```powershell
docker compose config --quiet
docker compose up --build -d
curl.exe http://localhost:8000/healthz
```

Open `http://localhost:8501` and verify a persona loads through the API. Use
`docker compose logs api ui` for failures and `docker compose down` for cleanup.
The grader uses this same launch path. A working Docker setup earns rubric points;
Docker failure alone is not an automatic milestone failure.
