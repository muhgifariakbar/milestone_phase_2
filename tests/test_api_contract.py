"""Additional API contract checks: auth ordering, 401/409/503 split, no leaked errors."""

from fastapi.testclient import TestClient

from src.api import create_app
from tests.fakes import FailingRouter, ScriptedRouter, example_database, failing_database


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_missing_header_is_401_and_no_find_called() -> None:
    # database=None (no Mongo configured at all) must not matter: the header
    # check must short-circuit before any repository is ever built or queried.
    client = TestClient(create_app())
    response = client.get("/api/v1/me/assessment")
    assert response.status_code == 401


def test_malformed_header_scheme_is_401() -> None:
    client = TestClient(create_app(example_database(), ScriptedRouter()))
    response = client.get("/api/v1/me/assessment", headers={"Authorization": "Token abc"})
    assert response.status_code == 401


def test_db_failure_during_auth_is_503() -> None:
    client = TestClient(create_app(failing_database(), ScriptedRouter()))
    response = client.get("/api/v1/me/assessment", headers=auth("any-token"))
    assert response.status_code == 503
    assert "RuntimeError" not in response.text
    assert "simulated" not in response.text


def test_assessment_db_failure_is_503() -> None:
    client = TestClient(create_app(failing_database(), ScriptedRouter()))
    response = client.get("/api/v1/me/assessment", headers=auth("public-token-a"))
    assert response.status_code == 503


def test_chat_db_failure_during_dispatch_is_503() -> None:
    # Token lookup needs its own working identity store; only downstream
    # assessment/balance lookups fail.
    database = example_database()
    from tests.fakes import FailingCollection

    database["customer_assessments"] = FailingCollection()
    client = TestClient(create_app(database, ScriptedRouter(tool_name="get_my_assessment")))
    response = client.post("/api/v1/chat", headers=auth("public-token-a"),
                           json={"message": "why this limit?", "history": []})
    assert response.status_code == 503


def test_chat_provider_failure_is_200_unavailable_not_503() -> None:
    client = TestClient(create_app(example_database(), FailingRouter()))
    response = client.post("/api/v1/chat", headers=auth("public-token-a"),
                           json={"message": "why this limit?", "history": []})
    assert response.status_code == 200
    assert response.json()["outcome"] == "unavailable"


def test_no_raw_exception_text_in_503_body() -> None:
    client = TestClient(create_app(failing_database(), ScriptedRouter()))
    response = client.get("/api/v1/me/assessment", headers=auth("any-token"))
    assert "Traceback" not in response.text
    assert "RuntimeError" not in response.text
