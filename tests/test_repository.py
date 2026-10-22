"""Unit tests for the identity-bound, read-only MongoDB repository."""

import pytest

from src.repository import Repository, RepositoryUnavailable
from tests.fakes import (
    balance_average_mismatch_database,
    capped_limit_database,
    contradictory_limit_database,
    contradictory_tier_database,
    empty_reason_codes_database,
    example_database,
    failing_database,
    malformed_reason_code_database,
    rounding_down_database,
    score_risk_mismatch_database,
    stale_model_version_database,
)


def test_customer_for_token_found() -> None:
    repo = Repository(example_database())
    identity = repo.customer_for_token("public-token-a")
    assert identity is not None
    assert identity["customer_id"] == "C90001"


def test_customer_for_token_not_found() -> None:
    repo = Repository(example_database())
    assert repo.customer_for_token("nonexistent") is None


def test_customer_for_token_db_failure_raises() -> None:
    repo = Repository(failing_database())
    with pytest.raises(RepositoryUnavailable):
        repo.customer_for_token("anything")


def test_assessment_valid_record_returns_expected_shape() -> None:
    repo = Repository(example_database())
    facts = repo.assessment("C90001")
    assert facts is not None
    assert facts["score"] == 740
    assert facts["tier"] == "lower risk"
    assert facts["credit_limit_idr"] == 12_000_000
    assert facts["average_balance_36m"] == 8_000_000
    assert facts["explanation_status"] == "available"
    assert facts["model_version"] == "synthetic-cart-v2"


def test_assessment_incomplete_history_returns_none() -> None:
    repo = Repository(example_database(incomplete=True))
    assert repo.assessment("C90001") is None


def test_assessment_stale_model_version_returns_none() -> None:
    repo = Repository(stale_model_version_database())
    assert repo.assessment("C90001") is None


def test_assessment_score_risk_mismatch_returns_none() -> None:
    repo = Repository(score_risk_mismatch_database())
    assert repo.assessment("C90001") is None


def test_assessment_balance_average_mismatch_returns_none() -> None:
    repo = Repository(balance_average_mismatch_database())
    assert repo.assessment("C90001") is None


def test_assessment_limit_mismatch_returns_none() -> None:
    repo = Repository(contradictory_limit_database())
    assert repo.assessment("C90001") is None


def test_assessment_tier_mismatch_returns_none() -> None:
    repo = Repository(contradictory_tier_database())
    assert repo.assessment("C90001") is None


def test_assessment_rounds_down_correctly() -> None:
    repo = Repository(rounding_down_database())
    facts = repo.assessment("C90001")
    assert facts is not None
    assert facts["credit_limit_idr"] == 8_200_000


def test_assessment_caps_at_100_million() -> None:
    repo = Repository(capped_limit_database())
    facts = repo.assessment("C90001")
    assert facts is not None
    assert facts["credit_limit_idr"] == 100_000_000


def test_assessment_empty_reason_codes_keeps_score_marks_unavailable() -> None:
    repo = Repository(empty_reason_codes_database())
    facts = repo.assessment("C90001")
    assert facts is not None
    assert facts["score"] == 740
    assert facts["credit_limit_idr"] == 12_000_000
    assert facts["explanation_status"] == "unavailable"
    assert facts["reason_codes"] == []


def test_assessment_malformed_reason_code_marks_unavailable() -> None:
    repo = Repository(malformed_reason_code_database())
    facts = repo.assessment("C90001")
    assert facts is not None
    assert facts["explanation_status"] == "unavailable"
    assert facts["reason_codes"] == []


def test_assessment_db_failure_raises() -> None:
    repo = Repository(failing_database())
    with pytest.raises(RepositoryUnavailable):
        repo.assessment("C90001")


def test_assessment_missing_record_returns_none() -> None:
    repo = Repository(example_database())
    assert repo.assessment("C00099") is None


def test_balance_summary_valid() -> None:
    repo = Repository(example_database())
    summary = repo.balance_summary("C90001")
    assert summary == {"average_balance_36m": 8_000_000, "month_count": 36}


def test_balance_summary_incomplete_returns_none() -> None:
    repo = Repository(example_database(incomplete=True))
    assert repo.balance_summary("C90001") is None


def test_balance_summary_db_failure_raises() -> None:
    repo = Repository(failing_database())
    with pytest.raises(RepositoryUnavailable):
        repo.balance_summary("C90001")
