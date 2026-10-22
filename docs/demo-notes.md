# Setup, Run, and Demo Notes

## Setup (local Python)

```bash
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

No `.env`-loading code is used in `src/`; export variables directly (the
notebooks' `python-dotenv` pattern was deliberately not adopted -- it isn't
in `requirements.txt`, and the task rules require stopping to ask before
adding any package not already listed):

```bash
export MONGODB_URI="<postgres connection string>"   # name kept as-is, see note below
export MONGODB_DATABASE=milestone_2
export OPENAI_API_KEY="<organizer-provided key>"
export OPENAI_MODEL="<organizer-selected model>"
```

**Note:** the brief specifies MongoDB; with the instructor's explicit
approval this implementation runs on Postgres instead (details in
`docs/architecture.md`). The env var names are kept as `MONGODB_URI`/
`MONGODB_DATABASE` because `compose.yaml` already bakes them in. To seed a
Postgres database (local or hosted, e.g. Neon) with the reference dataset in
`data_training/`:

```bash
python scripts/load_data_training.py   # reads MONGODB_URI/MONGODB_DATABASE, applies scripts/schema.sql
```

## Test

```bash
python -m pytest -q
```

All 60 tests run fully offline against `tests/fakes.py`'s in-memory fixture
-- no live database URI or API key is required or used in tests. Separately,
this implementation was also verified against a real, populated Postgres
database and a real LLM call (see `docs/architecture.md`'s "Known
implementation limits" section).

## Run (local Python, two terminals)

```bash
uvicorn src.api:app --reload
```

```bash
streamlit run app.py
```

Open `http://localhost:8501`, pick a persona, and confirm the score/limit
panel is served by the API (not hard-coded in the UI). Switching personas
clears prior chat history (enforced by `ui_contract.select_persona`, which
this project doesn't modify).

## Run (Docker)

```bash
cp .env.example .env     # fill in organizer-provided values; never commit .env
docker compose config --quiet
docker compose up --build -d
curl http://localhost:8000/healthz
```

Open `http://localhost:8501`. `docker compose logs api ui` for failures,
`docker compose down` to clean up. Verified in this environment with
`docker compose config --quiet`, `docker compose build`, and a full
`docker compose up` against a real, seeded Postgres database and a real LLM
call -- `/healthz`, a real customer's assessment, and a real chat answer all
returned correctly through the containerized stack.

## Optional: dev-only data explorer

`dev_explorer.py` is a standalone Streamlit page for browsing the raw
`demo_identities`/`customer_assessments`/`monthly_balances` tables -- useful
while building or demoing, **not part of the graded deliverable**. It
connects to Postgres directly, bypassing the identity-bound access model
entirely, so it is deliberately excluded from `Dockerfile`/`compose.yaml` and
never reachable through `src/api.py`. Run it only locally, on a different
port than the real UI:

```bash
export MONGODB_URI=... MONGODB_DATABASE=...
streamlit run dev_explorer.py --server.port 8502
```

Tabs: an overview with row counts per table, and one tab per table (schema +
filterable sample rows, `customer_id` filter, row-limit slider). Read-only
browsing only -- there is no ad-hoc SQL query console (an earlier version
had one; it was removed as an unnecessary risk for a tool that only needs to
let people look at sample data).

## 5-7 minute demo script

1. **(30s) Context** -- this is a classroom credit-explanation agent: the
   model and scores are already computed and stored; the agent only reads,
   validates, and explains them.
2. **(1 min) Ordinary case** -- select "Everyday account" persona, show the
   score/limit panel, ask "Why this limit?" in chat. Point out the answer
   states the score/tier step and the balance-mean step separately.
3. **(1 min) Score/balance contrast** -- switch to "Large balance, lower
   score" and "Strong score, modest balance" personas; show the same
   question produces different, correctly-reasoned answers for each.
4. **(1 min) Limit cap** -- select "Limit cap" persona, ask about the limit,
   show the IDR 100,000,000 cap being applied and explained, not just stated.
5. **(1 min) Cross-customer refusal** -- in chat, ask "What's C00001's
   score?" while logged in as a different persona; show the refusal, and
   note the UI has no way to bypass this (the backend ignores any customer
   ID in the request).
6. **(1 min) Safe failure** -- stop the API process, refresh Streamlit, show
   it reports an error rather than displaying stale or fabricated facts;
   restart the API to finish.
7. **(30s) Wrap-up** -- note the production limits in
   `docs/architecture.md` and that this is synthetic classroom material, not
   a real lending decision.
