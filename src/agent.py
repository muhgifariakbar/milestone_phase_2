"""Participant task: route chat to guarded tools and render grounded answers."""

from typing import Protocol

from .repository import Repository


class Router(Protocol):
    def route(self, message: str, history: list[dict[str, str]]) -> tuple[str, dict]: ...


class OpenAIRouter:
    def __init__(self, model: str):
        self.model = model

    def route(self, message: str, history: list[dict[str, str]]) -> tuple[str, dict]:
        # TODO: Use a configured model to choose one allowed read-only function.
        # Bind customer identity on the server; reject unknown tools/arguments.
        raise NotImplementedError


def answer(message: str, history: list[dict[str, str]], customer_id: str,
           repository: Repository, router: Router) -> tuple[str, str]:
    # TODO: Render numbers from repository facts only. Refuse other-customer requests.
    raise NotImplementedError
