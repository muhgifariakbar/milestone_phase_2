"""Confirms the participant's re-implemented policy math in src/repository.py
matches the organizer's own reference implementation in
provided_model/training_source/src/policy.py (not shipped in the runtime
Docker image -- this file is test-time-only rigor, not a runtime dependency).
"""

import importlib.util
from pathlib import Path

from src.repository import _expected_limit, _score_band  # our implementation

# Loaded by file path (not by package import) because both this project's
# package and the organizer's reference module are named "src" -- a plain
# `sys.path` + `import src.policy` would collide with the already-imported
# project package.
_POLICY_PATH = (Path(__file__).resolve().parents[1]
                 / "provided_model" / "training_source" / "src" / "policy.py")
_spec = importlib.util.spec_from_file_location("organizer_policy", _POLICY_PATH)
_organizer_policy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_organizer_policy)
credit_limit = _organizer_policy.credit_limit
score_tier = _organizer_policy.score_tier

SAMPLE_SCORES = [300, 410, 549, 550, 600, 649, 650, 700, 749, 750, 800, 850]
SAMPLE_BALANCES = [0, 1, 100_000, 999_999, 1_000_000, 8_000_000, 8_250_000,
                    50_000_000, 90_000_000, 100_000_000, 200_000_000]


def test_tier_labels_and_multipliers_match_reference() -> None:
    for score in SAMPLE_SCORES:
        ref_label, ref_multiplier = score_tier(score)
        ours = _score_band(score)
        assert ours is not None
        our_label, our_multiplier = ours
        assert our_label == ref_label
        assert our_multiplier == ref_multiplier


def test_credit_limit_matches_reference() -> None:
    for score in SAMPLE_SCORES:
        _, multiplier = score_tier(score)
        for balance in SAMPLE_BALANCES:
            expected = credit_limit(balance, score)
            ours = _expected_limit(balance, multiplier)
            assert ours == expected, (score, balance)
