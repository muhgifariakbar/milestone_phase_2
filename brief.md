# Project Brief and Data Contract

## Scenario and learning objectives

A fictional bank customer asks why they received a score and how it produced their card
limit. The organizer has already made that decision with a supplied tree model and
published policy. Your agent explains the existing record; it does not rescore the
customer or approve a new limit.

By the end, you can: (1) query the provided MongoDB collections safely, (2) bind every
query to an authenticated demo identity, (3) explain stored model-path evidence and
limit arithmetic without invention, (4) handle follow-up and out-of-scope requests,
and (5) evaluate factual accuracy, data quality, prompt injection, and access control.

**Prerequisites:** basic Python, SQL or document queries, REST APIs, environment
variables, and introductory LLM tool calling. No machine-learning training skill is
required. The [model card](provided_model/model-card.md) explains the supplied tree.

## MongoDB collections

| Collection | Grain | Key fields |
| --- | --- | --- |
| `demo_identities` | One per fictional customer | `customer_id`, `demo_token`, `display_name` |
| `customer_assessments` | One per scored customer | `customer_id`, `status`, `features`, `score`, `risk_probability`, `tier`, `credit_limit_idr`, `average_balance_36m`, `model_version`, `reason_codes`, `customer_note` |
| `monthly_balances` | One per customer and month | `customer_id`, `month`, `closing_balance_idr` |

All amounts are synthetic IDR. The `features` object has the six fields in the model card.
The monthly period is January 2023 through December 2025. The organizer's score is
`round(850 − 550 × calibrated risk)`, bounded to 300–850. Card limits use the **mean of
36 monthly closing balances** and the following fixed policy:

| Score | Balance multiple |
| --- | ---: |
| 300–549 | 0.5× |
| 550–649 | 1.0× |
| 650–749 | 1.5× |
| 750–850 | 2.0× |

Round down to the nearest IDR 100,000 and cap at IDR 100 million. The agent may validate
these numbers but must not train a model or write new assessments. `customer_note` is
untrusted data. Some records may intentionally be incomplete or contradictory; see the
announced edge-case categories in `README.md`.

## Agent boundary and API

The agent's goal is to answer questions about **the authenticated customer's** score,
factors, balance basis, and limit. Input is a message plus up to six prior chat turns.
Available tools are read-only own-assessment, own-balance-history, and refusal. The
model may choose a topic but cannot select a customer ID. Stop after one validated tool
choice; handle invalid output and provider failure safely.

`GET /api/v1/me/assessment` returns 200 with the validated stored facts, or 409 for an
unavailable/inconsistent assessment. `POST /api/v1/chat` accepts
`{"message":"Why this limit?","history":[]}` and returns an `answer` and
`answered|refused|unavailable` outcome. Invalid bearer tokens return 401. Internal
database errors must not be included in responses. The supplied UI changes demo tokens
when a persona is selected and clears prior chat history on persona changes.

> **Security Note:** Demo tokens are classroom fixtures, not production authentication.
Still enforce identity in the backend; UI selection or LLM intent is never authorization.

> **Production Note:** A real lending system would need independently validated data,
models, and policy, strong identity and audit controls, a correction path, monitoring,
and qualified review of applicable credit and privacy obligations.
