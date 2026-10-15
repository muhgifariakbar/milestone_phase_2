"""Checks for the provided UI adapter; these pass before the API is implemented."""

import httpx

from ui_contract import fetch_assessment, load_personas, select_persona, send_message


def test_public_personas_and_history_reset() -> None:
    from pathlib import Path

    personas = load_personas(Path("demo_personas.json"))
    assert len(personas) >= 5
    state = {"active_customer_id": personas[0]["customer_id"],
             "conversation": [{"role": "user", "content": "old"}]}
    select_persona(state, personas[1])
    assert state["conversation"] == []


def test_ui_uses_bearer_token_and_handles_failures() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer demo-token"
        if request.url.path.endswith("assessment"):
            return httpx.Response(409)
        return httpx.Response(503)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert fetch_assessment(client, "http://demo", "demo-token") == ("unavailable", None)
        assert send_message(client, "http://demo", "demo-token", "Why?", [])[1] == "error"
