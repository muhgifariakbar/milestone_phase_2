"""Participant task: authenticated FastAPI endpoints used by app.py."""

from fastapi import FastAPI

from .agent import Router


def create_app(database=None, router: Router | None = None) -> FastAPI:
    app = FastAPI(title="Synthetic Bank Credit Explanation Agent")

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    # TODO: Connect with MONGODB_URI and MONGODB_DATABASE, or use injected database in tests.
    # TODO: GET /api/v1/me/assessment (bearer auth; own MongoDB records only)
    # TODO: POST /api/v1/chat (bounded routing; no client-supplied customer ID)
    return app


app = create_app()
