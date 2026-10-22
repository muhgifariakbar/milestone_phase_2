"""The actual HTTP routes. This is FastAPI's `APIRouter` -- a small,
importable object you register endpoints on with `@router.get(...)` /
`@router.post(...)`, then plug into the real app with
`app.include_router(router)` (done in src/api/app.py). Splitting routes out
like this is the standard FastAPI pattern once an app has more than a
handful of endpoints, but the mechanics are identical to decorating these
same functions directly on a `FastAPI()` instance -- `APIRouter` is just a
container you assemble first and attach later.

Each route function's parameters that use `Depends(...)` are FastAPI
dependencies (see dependencies.py): FastAPI inspects the function signature,
figures out what each `Depends(...)` needs, calls it for you, and passes
the result in as that argument. You never call `authenticate(...)` or
`get_repository(...)` yourself here -- FastAPI does it, per request.
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..agent import Router as LLMRouter
from ..agent import answer
from ..repository import Repository, RepositoryUnavailable
from .dependencies import authenticate, get_llm_router, get_repository

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: list[dict[str, str]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    outcome: Literal["answered", "refused", "unavailable"]


class ReasonCode(BaseModel):
    feature: str
    observed_value: float
    threshold: float
    direction: str
    path_risk_change: float
    description: str


class AssessmentOut(BaseModel):
    score: int
    average_balance_36m: float
    credit_limit_idr: int
    as_of_date: str
    model_version: str
    tier: str
    reason_codes: list[ReasonCode]
    explanation_status: str


@router.get("/healthz")
def healthz() -> dict:
    """Public, no auth, no database -- just proves the process is alive."""
    return {"status": "ok"}


@router.get("/api/v1/me/assessment", response_model=AssessmentOut)
def get_my_assessment(
    identity: dict = Depends(authenticate),
    repository: Repository = Depends(get_repository),
) -> AssessmentOut:
    try:
        facts = repository.assessment(identity["customer_id"])
    except RepositoryUnavailable:
        raise HTTPException(status_code=503, detail="service unavailable")
    if facts is None:
        raise HTTPException(status_code=409, detail="assessment unavailable")
    return AssessmentOut(**facts)


@router.post("/api/v1/chat", response_model=ChatResponse)
def post_chat(
    body: ChatRequest,
    identity: dict = Depends(authenticate),
    repository: Repository = Depends(get_repository),
    llm_router: LLMRouter = Depends(get_llm_router),
) -> ChatResponse:
    try:
        text, outcome = answer(body.message, body.history, identity["customer_id"],
                                repository, llm_router)
    except RepositoryUnavailable:
        raise HTTPException(status_code=503, detail="service unavailable")
    except Exception:
        raise HTTPException(status_code=503, detail="service unavailable")
    return ChatResponse(answer=text, outcome=outcome)
