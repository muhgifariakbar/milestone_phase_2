"""Internal dev-only data browser + live agent demo (read-only, no ad-hoc
query console).

NOT part of the graded deliverable: it connects straight to Postgres and
bypasses the whole identity-bound access model this project enforces
everywhere else, so it is deliberately excluded from Dockerfile/compose.yaml
and never reachable through src/api.py. The "AI Agent" page reuses the exact
src/agent.py + src/repository.py code the graded API runs -- it just skips
the HTTP/bearer-token layer since this tool already has direct DB access.
Run it locally only:

    source .venv/bin/activate
    export MONGODB_URI=...   # same connection string as the real app
    export MONGODB_DATABASE=...
    export OPENAI_API_KEY=... OPENAI_MODEL=...   # only needed for the AI Agent page
    streamlit run dev_explorer.py --server.port 8502

Each section below is a real Streamlit multipage route (st.navigation/
st.Page), so it has a real URL -- e.g. http://localhost:8502/ai-agent opens
the AI Agent page directly.

Secrets (OPENAI_API_KEY, the database connection string) are read from
environment variables only and are never displayed, logged, or rendered to
the page anywhere in this file -- only someone with direct edit access to
this machine's .env or this project's deployment configuration can see them.
"""

import os
from pathlib import Path

import pandas as pd
import psycopg
import streamlit as st

from src.agent import LLMRouter
from src.agent import answer as agent_answer
from src.postgres_adapter import PostgresCollection
from src.repository import Repository, RepositoryUnavailable
from ui_contract import load_personas, select_persona

TABLES = ("demo_identities", "customer_assessments", "monthly_balances")
MAX_SAMPLE_ROWS = 200
PROJECT_OWNER = "muhgifariakbar"


def _dsn() -> str | None:
    uri = os.getenv("MONGODB_URI")
    if not uri:
        return None
    database = os.getenv("MONGODB_DATABASE")
    if database and "://" in uri:
        head, _, tail = uri.partition("://")
        if "/" not in tail.split("?", 1)[0]:
            path, _, query = tail.partition("?")
            tail = f"{path}/{database}" + (f"?{query}" if query else "")
            uri = f"{head}://{tail}"
    return uri


@st.cache_resource
def _connection(dsn: str) -> psycopg.Connection:
    return psycopg.connect(dsn, autocommit=True)


@st.cache_resource
def _repository(dsn: str) -> Repository:
    connection = _connection(dsn)
    return Repository({name: PostgresCollection(connection, name) for name in TABLES})


@st.cache_resource
def _router() -> LLMRouter:
    return LLMRouter(model=os.getenv("OPENAI_MODEL", ""))


def _live_connection(dsn: str) -> psycopg.Connection:
    """st.cache_resource caches the connection for the life of the process --
    Neon (serverless Postgres) can suspend or drop an idle connection out
    from under us, so without this, every rerun after that would keep
    reusing a dead connection forever. Probe it, and transparently rebuild
    (clearing the dependent _repository cache too) if it's gone."""
    connection = _connection(dsn)
    try:
        connection.execute("SELECT 1")
        return connection
    except Exception:
        _connection.clear()
        _repository.clear()
        connection = _connection(dsn)
        connection.execute("SELECT 1")  # let this raise if still broken
        return connection


def _table_columns(connection, table: str) -> pd.DataFrame:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = %s ORDER BY ordinal_position",
            [table],
        )
        rows = cursor.fetchall()
    return pd.DataFrame(rows, columns=["column", "type"])


def _table_count(connection, table: str) -> int:
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT count(*) FROM {table}")  # noqa: S608 (table is our own constant)
        return cursor.fetchone()[0]


def _table_sample(connection, table: str, customer_id: str, limit: int) -> pd.DataFrame:
    sql = f"SELECT * FROM {table}"  # noqa: S608 (table is our own constant)
    params: list = []
    if customer_id:
        sql += " WHERE customer_id = %s"
        params.append(customer_id)
    sql += " LIMIT %s"
    params.append(limit)
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        columns = [c.name for c in cursor.description]
        rows = cursor.fetchall()
    return pd.DataFrame(rows, columns=columns)


def _table_page(table: str):
    def render() -> None:
        st.subheader(f"Schema: {table}")
        st.dataframe(_table_columns(connection, table), hide_index=True, width="stretch")
        st.subheader("Sample rows")
        col1, col2 = st.columns([2, 1])
        customer_filter = col1.text_input("Filter by customer_id (optional)", key=f"filter_{table}")
        limit = col2.slider("Row limit", 1, MAX_SAMPLE_ROWS, 20, key=f"limit_{table}")
        try:
            st.dataframe(_table_sample(connection, table, customer_filter, limit),
                        width="stretch")
        except Exception as exc:
            st.error(f"Query failed: {exc}")
    return render


def page_overview() -> None:
    st.subheader("Tables")
    overview_rows = []
    for table in TABLES:
        try:
            overview_rows.append({"table": table, "rows": _table_count(connection, table)})
        except Exception as exc:
            overview_rows.append({"table": table, "rows": f"error: {exc}"})
    st.dataframe(pd.DataFrame(overview_rows), hide_index=True, width="stretch")
    st.caption(
        "demo_identities: one row per fictional customer (customer_id, demo_token). "
        "customer_assessments: one scored record per customer (score, tier, limit, "
        "reason_codes, customer_note). monthly_balances: one row per customer per "
        "month, Jan 2023-Dec 2025 (36 rows/customer when complete)."
    )
    st.divider()
    st.markdown("### ✨ Try the real AI agent")
    st.caption(
        "Pick a persona and chat with the exact agent code the graded API "
        "runs -- live, against this database."
    )
    st.page_link(agent_page, label="Open the AI Agent →", icon="✨")


def page_ai_agent() -> None:
    st.success(
        "✨ **Live agent demo** -- this runs the exact same `src/agent.py` + "
        "`src/repository.py` code the graded API uses, directly against this "
        "database. No bearer token is needed here (this tool already bypasses "
        "that HTTP layer), but the agent still can't be talked into revealing "
        "another persona's data -- try asking about a different customer_id "
        "and see the refusal."
    )

    try:
        personas = load_personas(Path("demo_personas.json"))
    except (OSError, ValueError) as exc:
        personas = []
        st.error(f"Could not load demo_personas.json: {exc}")

    if not personas:
        st.warning("No personas available.")
        return

    labels = [f"{p['customer_id']} -- {p['label']} -- {p['scenario']}" for p in personas]
    selected_index = st.selectbox(
        "Choose a customer to chat as",
        range(len(personas)),
        format_func=lambda i: labels[i],
        help=(
            "Each option is a different fictional customer (a 'persona') with "
            "its own stored score, balance history, and credit limit -- "
            "exactly like switching personas in the real app. Switching here "
            "clears the conversation below and starts fresh as that customer."
        ),
        key="agent_persona_index",
    )
    selected_persona = personas[selected_index]

    if "active_customer_id" not in st.session_state:
        st.session_state.active_customer_id = None
        st.session_state.conversation = []
    select_persona(st.session_state, selected_persona)

    st.caption(f"Acting as customer `{selected_persona['customer_id']}` -- "
              f"{selected_persona['scenario']}")

    try:
        facts = _repository(dsn).assessment(selected_persona["customer_id"])
    except RepositoryUnavailable:
        facts = None
        st.error("The database is temporarily unavailable.")
    else:
        if facts is not None:
            left, middle, right = st.columns(3)
            left.metric("Classroom score", f"{facts['score']} / 850")
            middle.metric("36-month average", f"IDR {facts['average_balance_36m']:,.0f}")
            right.metric("Classroom card limit", f"IDR {facts['credit_limit_idr']:,}")
            st.caption(f"Assessment date: {facts['as_of_date']} · Model: {facts['model_version']}")
            if facts.get("explanation_status") == "available":
                with st.expander("Model-path evidence"):
                    for reason in facts["reason_codes"]:
                        st.write(f"• {reason['description']}")
            else:
                st.warning("Verified reason evidence is unavailable. Ask for a record review.")
        else:
            st.warning("This customer's assessment is unavailable -- incomplete "
                       "or internally inconsistent stored data. Ask the agent for "
                       "an explanation; it will safely decline too.")

    st.divider()
    for turn in st.session_state.conversation:
        with st.chat_message(turn["role"]):
            st.write(turn["content"])

    question = st.chat_input("Ask about this persona's score, balance, or limit")
    if question:
        try:
            reply, outcome = agent_answer(
                question, st.session_state.conversation,
                selected_persona["customer_id"], _repository(dsn), _router(),
            )
        except RepositoryUnavailable:
            reply, outcome = "The database is temporarily unavailable.", "unavailable"
        except Exception:
            reply, outcome = "Something went wrong handling that request.", "unavailable"
        st.session_state.conversation.extend([
            {"role": "user", "content": question[:1000]},
            {"role": "assistant", "content": reply[:1000]},
        ])
        st.caption(f"outcome: `{outcome}`")
        st.rerun()


def page_how_it_works() -> None:
    st.subheader("How this works, end to end")
    st.markdown(
        """
1. **You pick a persona** (or, in the real app, select one and log in with its
   demo token). This tool skips the token/HTTP layer and reads the persona's
   `customer_id` directly, since it already has its own DB access.
2. **Your message, a system prompt, and up to your last 6 chat turns** go to
   the LLM. It may choose only one of three actions -- explain my assessment,
   explain my balance history, or refuse -- and it is never told or allowed to
   guess a customer ID.
3. **That action triggers one read-only database lookup**, scoped to the one
   persona you picked on the server side -- never to anything the message
   text or the LLM says.
4. **The database layer independently re-validates everything** before
   trusting it: all 36 months present, the score matches the recomputed risk
   probability, the tier/multiplier and rounding/cap math check out. If
   anything is missing or inconsistent, it safely declines rather than
   guessing or repairing it.
5. **All numbers, dates, and reasons in the final answer are formatted by
   plain Python code**, never phrased by the LLM -- so it cannot invent a
   score, a limit, or a reason.
6. **A hidden guardrail runs before any of the above**: if your message or
   chat history names a different customer, the request is refused
   immediately and the LLM is never even called.
        """
    )
    st.subheader("Security")
    st.markdown(
        f"""
- The database connection string and `OPENAI_API_KEY` are read once from
  environment variables at startup and are **never** written to this page,
  a log, or an API response -- there is no code path in this project that
  prints or returns either of them.
- The only way to see their real values is direct edit access to this
  machine's local `.env` file or to **{PROJECT_OWNER}**'s own deployment
  configuration (e.g. the hosting provider's environment variables) --
  nothing reachable from this page exposes them.
- `.env` is excluded from git (`.gitignore`); this tool itself is excluded
  from the Docker image and `compose.yaml`, so it never ships anywhere.
        """
    )


st.set_page_config(page_title="Dev data explorer", page_icon="🛠️", layout="wide")
st.markdown(
    """
    <style>
    .stApp, [data-testid="stHeader"] { background-color: #0e1117; }
    .stApp, .stApp p, .stApp li, .stApp span { color: #fafafa; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🛠️ Dev data explorer")
st.caption(
    f"👤 Personal project by **{PROJECT_OWNER}** -- built as a hands-on milestone "
    "exploring bounded LLM agents, identity-bound data access, and safe-failure "
    "design. All data is synthetic classroom material; this is not a real bank "
    "or a real lending decision."
)
st.warning(
    "Internal dev tool only. Connects directly to the database with no "
    "identity boundary -- never deploy this, never use a customer demo token "
    "as if it applied here. It is excluded from Dockerfile/compose.yaml. "
    "Read-only browsing only -- there is no ad-hoc query console here."
)

dsn = _dsn()
if not dsn:
    st.error("MONGODB_URI is not set. Export it (and MONGODB_DATABASE) before running this.")
    st.stop()

try:
    connection = _live_connection(dsn)
except Exception as exc:
    st.error(f"Could not connect to the database: {exc}")
    st.stop()

overview_page = st.Page(page_overview, title="Overview", icon="📊",
                        url_path="overview", default=True)
agent_page = st.Page(page_ai_agent, title="AI Agent", icon="✨", url_path="ai-agent")
identities_page = st.Page(_table_page("demo_identities"), title="demo_identities",
                          icon="🪪", url_path="demo-identities")
assessments_page = st.Page(_table_page("customer_assessments"), title="customer_assessments",
                           icon="📈", url_path="customer-assessments")
balances_page = st.Page(_table_page("monthly_balances"), title="monthly_balances",
                        icon="💰", url_path="monthly-balances")
howitworks_page = st.Page(page_how_it_works, title="How it works", icon="❓",
                          url_path="how-it-works")

nav = st.navigation(
    [overview_page, agent_page, identities_page, assessments_page, balances_page,
     howitworks_page],
    position="top",
)
nav.run()
