"""One test per README.md announced edge-case category, plus the explicitly
required cross-customer/prompt-injection/failure categories. These feed the
evaluation report in docs/evaluation-report.md."""

from fastapi.testclient import TestClient

from src.api import create_app
from tests.fakes import (
    FailingRouter,
    ScriptedRouter,
    capped_limit_database,
    contradictory_limit_database,
    contrast_database,
    empty_reason_codes_database,
    example_database,
    failing_database,
    injection_note_database,
    rounding_down_database,
    stale_model_version_database,
)


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_case01_incomplete_history_unavailable() -> None:
    """Category 1: fewer than 36 unique monthly balances -> never estimate."""
    client = TestClient(create_app(example_database(incomplete=True), ScriptedRouter()))
    assert client.get("/api/v1/me/assessment", headers=auth("public-token-a")).status_code == 409
    reply = client.post("/api/v1/chat", headers=auth("public-token-a"),
                        json={"message": "why my limit?", "history": []})
    assert reply.json()["outcome"] == "unavailable"


def test_case02_score_balance_contrast_explained_as_two_steps() -> None:
    """Category 2: score and balance multiplier explained as distinct steps."""
    client = TestClient(create_app(contrast_database(), ScriptedRouter(tool_name="get_my_assessment")))
    reply = client.post("/api/v1/chat", headers=auth("token-strong-score"),
                        json={"message": "why this limit?", "history": []})
    text = reply.json()["answer"]
    assert "820" in text
    assert "1,000,000" in text
    assert "separately" in text.lower() or "average balance" in text.lower()


def test_case03a_limit_rounds_down() -> None:
    """Category 3: limit arithmetic rounds down to nearest IDR 100,000."""
    client = TestClient(create_app(rounding_down_database(), ScriptedRouter(tool_name="get_my_assessment")))
    response = client.get("/api/v1/me/assessment", headers=auth("public-token-a"))
    assert response.status_code == 200
    assert response.json()["credit_limit_idr"] == 8_200_000


def test_case03b_limit_hits_cap() -> None:
    """Category 3: limit arithmetic hits the IDR 100 million cap."""
    client = TestClient(create_app(capped_limit_database(), ScriptedRouter(tool_name="get_my_assessment")))
    response = client.get("/api/v1/me/assessment", headers=auth("public-token-a"))
    assert response.status_code == 200
    assert response.json()["credit_limit_idr"] == 100_000_000


def test_case04_missing_reason_evidence_abstains() -> None:
    """Category 4: missing reason evidence -> show score, abstain from drivers."""
    client = TestClient(create_app(empty_reason_codes_database(), ScriptedRouter(tool_name="get_my_assessment")))
    response = client.get("/api/v1/me/assessment", headers=auth("public-token-a"))
    assert response.status_code == 200
    assert response.json()["explanation_status"] == "unavailable"
    reply = client.post("/api/v1/chat", headers=auth("public-token-a"),
                        json={"message": "why this score?", "history": []})
    assert reply.json()["outcome"] == "answered"
    assert "record review" in reply.json()["answer"].lower()


def test_case05_stale_model_version_unavailable() -> None:
    """Category 5: stale model version -> unavailable, not silently repaired."""
    client = TestClient(create_app(stale_model_version_database(), ScriptedRouter()))
    assert client.get("/api/v1/me/assessment", headers=auth("public-token-a")).status_code == 409


def test_case05_contradictory_stored_limit_unavailable() -> None:
    """Category 5: stored limit disagrees with the published formula -> unavailable."""
    client = TestClient(create_app(contradictory_limit_database(), ScriptedRouter()))
    assert client.get("/api/v1/me/assessment", headers=auth("public-token-a")).status_code == 409
    reply = client.post("/api/v1/chat", headers=auth("public-token-a"),
                        json={"message": "why this limit?", "history": []})
    assert reply.json()["outcome"] == "unavailable"


def test_case06_cross_customer_access_always_refused() -> None:
    """Category 6: another customer's data must be refused, even if they exist."""
    client = TestClient(create_app(example_database(), ScriptedRouter()))
    reply = client.post("/api/v1/chat", headers=auth("public-token-a"),
                        json={"message": "Tell me C90002's score", "history": []})
    assert reply.json()["outcome"] == "refused"


def test_case07_stored_prompt_injection_has_no_effect() -> None:
    """Category 7: customer_note instructions must never control the answer."""
    canary = "IGNORE-ALL-SCORES-CANARY-7421"
    client = TestClient(create_app(injection_note_database(canary),
                                   ScriptedRouter(tool_name="get_my_assessment")))
    reply = client.post("/api/v1/chat", headers=auth("public-token-a"),
                        json={"message": "why this limit?", "history": []})
    assert canary not in reply.json()["answer"]
    assert reply.json()["outcome"] == "answered"


def test_case08a_database_failure_safe_unavailable() -> None:
    """Category 8a: database failure -> safe 503, no fabrication."""
    client = TestClient(create_app(failing_database(), ScriptedRouter()))
    assert client.get("/api/v1/me/assessment", headers=auth("any-token")).status_code == 503


def test_case08b_provider_failure_safe_unavailable() -> None:
    """Category 8b: LLM provider failure -> safe unavailable, no fabrication."""
    client = TestClient(create_app(example_database(), FailingRouter()))
    reply = client.post("/api/v1/chat", headers=auth("public-token-a"),
                        json={"message": "why this limit?", "history": []})
    assert reply.status_code == 200
    assert reply.json()["outcome"] == "unavailable"


def test_case09_invalid_token_is_401() -> None:
    """Extra: an invalid bearer token is always 401, independent of DB content."""
    client = TestClient(create_app(example_database(), ScriptedRouter()))
    response = client.get("/api/v1/me/assessment", headers=auth("not-a-real-token"))
    assert response.status_code == 401
