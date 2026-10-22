"""Shared, per-request dependencies: "what does every route need before it
can run". FastAPI calls these for you when a route declares
`Depends(authenticate)` etc. -- this file has no routes in it, only the
plumbing routes lean on.

Naming note: this project has two different things called a "router" and
they are NOT the same concept --
  - `get_llm_router()` below builds the LLM TOOL router from src/agent.py
    (picks one of 3 tool names for a chat message).
  - `src/api/router.py` is FastAPI's URL router (maps HTTP paths to
    functions).
They happen to share an English word; nothing else connects them.
"""

import os

from fastapi import Header, HTTPException, Request

from .. import agent as agent_module
from ..agent import Router as LLMRouter
from ..repository import Repository, RepositoryUnavailable


def get_repository(request: Request) -> Repository:
    """Returns the app's database access object, building (or rebuilding, if
    the cached connection died) a real Postgres-backed one on first use.

    Instructor-approved: Postgres backs this instead of MongoDB. The env var
    names (MONGODB_URI/MONGODB_DATABASE) are kept as-is because compose.yaml
    already bakes them in and isn't ours to edit.
    """
    state = request.app.state

    # A database injected by the caller (always true in tests) is used
    # as-is, forever -- this function never touches or replaces it.
    if state.repository_injected:
        return state.repository

    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise RepositoryUnavailable("MONGODB_URI is not configured")

    # Reuse the cached connection only if it's still actually alive. Neon
    # (and serverless Postgres generally) can suspend or drop an idle
    # connection out from under us; without this check, every request after
    # that would silently 503 forever even though a brand-new connection
    # works fine -- this was a real bug found via live testing.
    if state.db_connection is not None:
        try:
            state.db_connection.execute("SELECT 1")
            return state.repository
        except Exception:
            state.db_connection = None
            state.repository = None

    import psycopg

    from ..postgres_adapter import PostgresCollection, resolve_dsn

    dsn = resolve_dsn(uri, os.getenv("MONGODB_DATABASE"))
    try:
        connection = psycopg.connect(dsn, autocommit=True, connect_timeout=5)
    except Exception as exc:
        raise RepositoryUnavailable("could not connect to database") from exc
    state.db_connection = connection
    state.repository = Repository({
        name: PostgresCollection(connection, name)
        for name in ("demo_identities", "customer_assessments", "monthly_balances")
    })
    return state.repository


def get_llm_router(request: Request) -> LLMRouter:
    """Returns the app's LLM tool router, building the real one (OpenAI via
    LangChain, see src/agent.py's LLMRouter) on first use."""
    state = request.app.state
    if state.llm_router is None:
        state.llm_router = agent_module.LLMRouter(model=os.getenv("OPENAI_MODEL", ""))
    return state.llm_router


def authenticate(request: Request, authorization: str | None = Header(default=None)) -> dict:
    """Resolves the bearer token to a customer identity. This is the only
    place a client-supplied token ever turns into a customer_id -- nothing
    downstream trusts any other source for one.

    Deliberately calls get_repository() as a plain function, not via
    Depends(get_repository): a request with no/invalid Authorization header
    must get a clean 401 WITHOUT ever touching the database. If this were a
    Depends() sub-dependency instead, FastAPI would resolve it before this
    function's body runs at all, regardless of parameter order -- an actual
    bug this project hit once already.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="invalid or missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="invalid or missing bearer token")
    try:
        repository = get_repository(request)
        identity = repository.customer_for_token(token)
    except RepositoryUnavailable:
        raise HTTPException(status_code=503, detail="service unavailable")
    if identity is None:
        raise HTTPException(status_code=401, detail="invalid or missing bearer token")
    return identity
