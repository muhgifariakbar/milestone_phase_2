"""Builds the actual FastAPI application. This is the only place
`FastAPI()` gets constructed -- everything else (routes, dependencies)
just gets attached to the object this file creates.
"""

from fastapi import FastAPI

from ..agent import Router as LLMRouter
from ..repository import Repository
from .router import router as api_router


def create_app(database=None, router: LLMRouter | None = None) -> FastAPI:
    """`database`/`router` let tests inject a fake Mongo-like store and a
    scripted LLM router instead of real ones -- see tests/fakes.py. Neither
    is required: calling create_app() with no arguments (what
    `app = create_app()` below does, and what the Dockerfile's
    `uvicorn src.api:app` imports) builds real connections lazily, on first
    request, never at import time.
    """
    app = FastAPI(title="Synthetic Bank Credit Explanation Agent")

    # Everything below is state shared across requests for the life of this
    # one app instance -- see dependencies.py for how it gets used/rebuilt.
    app.state.repository_injected = database is not None
    app.state.repository = Repository(database) if database is not None else None
    app.state.db_connection = None
    app.state.llm_router = router

    app.include_router(api_router)
    return app


app = create_app()
