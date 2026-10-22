"""Unit tests for the bounded explanation agent."""

from src.agent import answer
from src.repository import Repository
from tests.fakes import FailingRouter, ScriptedRouter, example_database, injection_note_database


def test_cross_customer_id_in_message_is_refused_without_calling_router() -> None:
    repo = Repository(example_database())
    router = ScriptedRouter()
    text, outcome = answer("Tell me C90002's score", [], "C90001", repo, router)
    assert outcome == "refused"
    assert router.called is False


def test_cross_customer_id_in_history_is_refused() -> None:
    repo = Repository(example_database())
    router = ScriptedRouter()
    history = [{"role": "user", "content": "what about C90002"},
               {"role": "assistant", "content": "I can't discuss that"}]
    text, outcome = answer("ok then what's my score", history, "C90001", repo, router)
    assert outcome == "refused"
    assert router.called is False


def test_own_customer_id_in_message_is_not_refused() -> None:
    repo = Repository(example_database())
    router = ScriptedRouter()
    text, outcome = answer("What is C90001's score?", [], "C90001", repo, router)
    assert outcome == "answered"
    assert router.called is True


def test_provider_failure_returns_unavailable_not_exception() -> None:
    repo = Repository(example_database())
    text, outcome = answer("Why this limit?", [], "C90001", repo, FailingRouter())
    assert outcome == "unavailable"


def test_unknown_tool_name_is_unavailable() -> None:
    repo = Repository(example_database())
    router = ScriptedRouter(tool_name="drop_all_records", args={})
    text, outcome = answer("hi", [], "C90001", repo, router)
    assert outcome == "unavailable"


def test_disallowed_arg_key_is_unavailable() -> None:
    repo = Repository(example_database())
    router = ScriptedRouter(tool_name="get_my_assessment", args={"customer_id": "C90002"})
    text, outcome = answer("hi", [], "C90001", repo, router)
    assert outcome == "unavailable"


def test_non_string_arg_value_is_unavailable() -> None:
    repo = Repository(example_database())
    router = ScriptedRouter(tool_name="get_my_assessment", args={"topic": 123})
    text, outcome = answer("hi", [], "C90001", repo, router)
    assert outcome == "unavailable"


def test_refuse_tool_choice_yields_refused_outcome() -> None:
    repo = Repository(example_database())
    router = ScriptedRouter(tool_name="refuse", args={"reason": "out of scope"})
    text, outcome = answer("tell me a joke", [], "C90001", repo, router)
    assert outcome == "refused"


def test_answer_numbers_match_repository_exactly() -> None:
    repo = Repository(example_database())
    router = ScriptedRouter(tool_name="get_my_assessment")
    text, outcome = answer("Why is my limit 12 million?", [], "C90001", repo, router)
    assert outcome == "answered"
    assert "12,000,000" in text
    assert "740" in text


def test_customer_note_absent_from_router_call_and_from_answer_text() -> None:
    canary = "IGNORE-ALL-SCORES-CANARY-7421"
    repo = Repository(injection_note_database(canary))
    router = ScriptedRouter(tool_name="get_my_assessment")
    text, outcome = answer("Why this limit?", [], "C90001", repo, router)
    assert outcome == "answered"
    assert canary not in text
    message, history = router.last_call
    assert canary not in message
    assert all(canary not in turn.get("content", "") for turn in history)


def test_repositoryunavailable_during_dispatch_propagates_uncaught() -> None:
    from src.repository import RepositoryUnavailable
    from tests.fakes import failing_database
    import pytest

    repo = Repository(failing_database())
    router = ScriptedRouter(tool_name="get_my_assessment")
    with pytest.raises(RepositoryUnavailable):
        answer("Why this limit?", [], "C90001", repo, router)


def test_missing_reason_codes_abstains_and_offers_review() -> None:
    from tests.fakes import empty_reason_codes_database

    repo = Repository(empty_reason_codes_database())
    router = ScriptedRouter(tool_name="get_my_assessment")
    text, outcome = answer("why this score?", [], "C90001", repo, router)
    assert outcome == "answered"
    assert "record review" in text
    assert "740" in text


def test_history_is_truncated_to_six_turns_before_scan_and_route() -> None:
    repo = Repository(example_database())
    router = ScriptedRouter()
    long_history = [{"role": "user", "content": f"turn {i}"} for i in range(10)]
    answer("why this limit?", long_history, "C90001", repo, router)
    _, passed_history = router.last_call
    assert len(passed_history) == 6
    assert passed_history[0]["content"] == "turn 4"
