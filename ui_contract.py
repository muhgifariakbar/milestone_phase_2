"""Testable persona and API behavior shared by the supplied Streamlit client."""

import json
from pathlib import Path

import httpx


def load_personas(path: Path) -> list[dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("nonempty demo persona catalog required")
    for row in rows:
        if not all(row.get(key) for key in ("customer_id", "label", "scenario", "demo_token")):
            raise ValueError("invalid demo persona")
    return rows


def select_persona(state: dict, persona: dict) -> None:
    if state.get("active_customer_id") != persona["customer_id"]:
        state["active_customer_id"] = persona["customer_id"]
        state["conversation"] = []


def fetch_assessment(client: httpx.Client, base_url: str, token: str) -> tuple[str, dict | None]:
    try:
        response = client.get(f"{base_url}/api/v1/me/assessment",
                              headers={"Authorization": f"Bearer {token}"})
    except httpx.HTTPError:
        return "error", None
    if response.status_code == 200:
        try:
            facts = response.json()
            required = ("score", "average_balance_36m", "credit_limit_idr",
                        "as_of_date", "model_version", "reason_codes", "explanation_status")
            if not isinstance(facts, dict) or any(key not in facts for key in required):
                return "error", None
            if (not isinstance(facts["reason_codes"], list)
                    or not all(isinstance(facts[key], (int, float)) for key in
                               ("score", "average_balance_36m", "credit_limit_idr"))
                    or not all(isinstance(facts[key], str) for key in
                               ("as_of_date", "model_version", "explanation_status"))):
                return "error", None
            return "available", facts
        except ValueError:
            return "error", None
    if response.status_code == 409:
        return "unavailable", None
    return "error", None


def send_message(client: httpx.Client, base_url: str, token: str,
                 message: str, history: list[dict]) -> tuple[str, str]:
    try:
        response = client.post(
            f"{base_url}/api/v1/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": message, "history": history[-6:]},
        )
    except httpx.HTTPError:
        return "Chat is temporarily unavailable.", "error"
    if response.status_code != 200:
        return "Chat is temporarily unavailable.", "error"
    try:
        payload = response.json()
        if payload["outcome"] not in {"answered", "refused", "unavailable"}:
            raise ValueError("invalid outcome")
        return str(payload["answer"]), payload["outcome"]
    except (ValueError, KeyError, TypeError):
        return "Chat is temporarily unavailable.", "error"
