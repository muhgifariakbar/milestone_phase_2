"""Participant task: authenticated FastAPI endpoints used by app.py.

This is split into three files, each doing one job:
  - dependencies.py  -- auth + "get me a working database/LLM router"
  - router.py         -- the actual routes (/healthz, /api/v1/me/assessment, /api/v1/chat)
  - app.py            -- builds the FastAPI() app and wires router.py into it

This file just re-exports `app`/`create_app` so nothing outside this
package needs to know it's a package at all: `uvicorn src.api:app` and
`from src.api import create_app` work exactly as if this were one file.
"""

from .app import app, create_app

__all__ = ["app", "create_app"]
