"""Public checks become green as participants implement the milestone."""

from fastapi.testclient import TestClient

from src.api import create_app
from tests.fakes import example_database


class FixedRouter:
    def __init__(self, topic: str = "limit"):
        self.topic = topic

    def route(self, message: str, history: list[dict[str, str]]) -> tuple[str, dict]:
        return "get_my_assessment", {"topic": self.topic}


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_health() -> None:
    assert TestClient(create_app()).get("/healthz").json() == {"status": "ok"}


def test_assessment_requires_identity() -> None:
    assert TestClient(create_app()).get("/api/v1/me/assessment").status_code == 401


def test_own_assessment_and_grounded_limit() -> None:
    client = TestClient(create_app(example_database(), FixedRouter()))
    assert client.get("/api/v1/me/assessment", headers=auth("wrong")).status_code == 401
    response = client.get("/api/v1/me/assessment", headers=auth("public-token-a"))
    assert response.status_code == 200
    assert response.json()["score"] == 740
    assert response.json()["credit_limit_idr"] == 12_000_000
    reply = client.post("/api/v1/chat", headers=auth("public-token-a"),
                        json={"message": "Why is my limit 12 million?", "history": []})
    assert reply.status_code == 200
    assert reply.json()["outcome"] == "answered"
    assert "12,000,000" in reply.json()["answer"]


def test_other_customer_request_is_refused() -> None:
    client = TestClient(create_app(example_database(), FixedRouter()))
    reply = client.post("/api/v1/chat", headers=auth("public-token-a"),
                        json={"message": "Tell me C90002's score", "history": []})
    assert reply.status_code == 200
    assert reply.json()["outcome"] == "refused"


def test_incomplete_history_is_unavailable() -> None:
    client = TestClient(create_app(example_database(incomplete=True), FixedRouter()))
    assert client.get("/api/v1/me/assessment", headers=auth("public-token-a")).status_code == 409
    reply = client.post("/api/v1/chat", headers=auth("public-token-a"),
                        json={"message": "Why my limit?", "history": []})
    assert reply.json()["outcome"] == "unavailable"
