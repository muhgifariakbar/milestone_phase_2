# Architecture Note

## Data flow

```text
Streamlit (app.py)
    | demo token selected via persona dropdown; chat history reset on switch
    v
POST/GET  Authorization: Bearer <demo-token>
    v
FastAPI (src/api.py)
    | 1. parse bearer header -> 401 if missing/malformed, no DB call
    | 2. Repository.customer_for_token(token) -> identity or 401; DB error -> 503
    v
Agent (src/agent.py)
    | 3. truncate history to last 6 turns
    | 4. scan message+history for any OTHER customer ID -> refuse, skip LLM
    | 5. router.route(message, history) chooses ONE of:
    |      get_my_assessment | get_my_balance_summary | refuse
    |    (model may pick a topic/tool; it never supplies a customer_id)
    v
Repository (src/repository.py)
    | 6. query customer_assessments / monthly_balances for the
    |    SERVER-RESOLVED customer_id only (never a client- or LLM-supplied id)
    | 7. independently recompute: 36-unique-month check, score<->risk_probability
    |    consistency, stored vs. recomputed average balance, tier/multiplier,
    |    rounding-down to IDR 100,000, IDR 100,000,000 cap, reason_codes shape
    | 8. return a validated facts dict, or None if anything is incomplete,
    |    stale, or internally contradictory
    v
Trusted rendering (src/agent.py)
    | 9. format score, dates, arithmetic, and reason text with plain Python
    |    string formatting -- the LLM never phrases numbers or facts
    v
Response: {"answer": ..., "outcome": "answered|refused|unavailable"}
    or   {score, average_balance_36m, credit_limit_idr, as_of_date,
          model_version, tier, reason_codes, explanation_status}
```

**Note on data store:** the brief specifies MongoDB; with the instructor's
explicit approval this implementation uses Postgres instead (a hosted Neon
instance in this environment). `src/repository.py` never talks to a specific
driver -- it only calls `.find()`/`.find_one()` on whatever's injected, so the
same validation logic, and all 60 fake-backed tests, are completely
unaffected by the swap. `src/postgres_adapter.py` is the only new code: a
thin adapter translating that same `.find()`/`.find_one()` interface into
parameterized SQL over three tables (`scripts/schema.sql`) that mirror
`brief.md`'s documented collections field-for-field. The env var names
(`MONGODB_URI`/`MONGODB_DATABASE`) are kept as-is since `compose.yaml`
already bakes them in and isn't ours to edit.

`customer_note` is read from the database only as inert stored data; it is never
passed to the LLM, never interpolated into a prompt, and never surfaced in an
answer. This is deliberate: the stored note is untrusted (edge case 7,
`rubric.md`'s hard gate on prompt injection), so the simplest safe design is
to never let it enter any code path that could act on it.

## Why a high balance can coexist with a lower score

The score comes from the organizer's fitted tree over six behavioral features
(on-time payments, overdrafts, late payments, balance volatility, inflow
stability, and the 36-month average balance itself as one of six inputs) --
balance size is only one input among six, and the published card-limit
*policy* then applies a **separate** step: a score-band multiplier against
the 36-month mean. A customer can have a large average balance but weak
payment behavior (lower score, smaller multiplier) or a strong score with a
modest balance (good multiplier, but a small base to multiply). The agent
always explains these as two distinct, separately-labeled steps rather than
one blended number.

## Production limits (expanding `brief.md`'s Production Note)

This is a classroom artifact and must not be presented as a real lending
decision. A production system would additionally need:
- Independently validated training data, model, and policy (not just an
  internal consistency check against a single stored record).
- Real identity verification and audit logging (demo bearer tokens are
  classroom fixtures, not authentication).
- A correction/appeal path for customers who dispute a stored assessment,
  instead of only "request a record review."
- Monitoring for model drift, data-pipeline failures, and anomalous query
  patterns (e.g. repeated cross-customer probing).
- Qualified legal/compliance review of applicable credit and privacy
  obligations (e.g. adverse-action notice requirements) before any of this
  logic could inform an actual decision.

## Known implementation limits

- Beyond the 60 fake-backed tests, this was also verified live: all 2,400
  real customer records in `data_training/` were loaded into Postgres
  (`scripts/load_data_training.py`) and independently re-validated by
  `Repository.assessment()` with zero false rejections, and the full stack
  (Postgres + FastAPI + Streamlit, all via `docker compose up`, plus a real
  `OpenAIRouter.route()` call against a live model) was exercised end-to-end
  through real HTTP requests -- not just unit tests against mocks.
- `OpenAIRouter` needed one adaptive fix discovered during that live test:
  some reasoning-tier models reject tool/function calls unless
  `reasoning_effort="none"` is passed explicitly; `route()` tries that first
  and falls back to omitting it if the model doesn't recognize the
  parameter, so it isn't tied to one specific model family.
- The tier/rounding/cap policy is re-implemented in `src/repository.py`
  (not imported from `provided_model/`, so the runtime image has no
  dependency on reference-only material); `tests/test_policy_cross_check.py`
  asserts it matches the organizer's own `provided_model/training_source/
  src/policy.py` exactly across a range of sample scores and balances.
