"""013M: decision gain gate (DL-012)."""

from src.review.candidate import Candidate
from src.review.gate import evaluate_decision_gain


def _cand(decision_gain: str) -> Candidate:
    return Candidate(
        action="CLASS",
        label="x",
        rationale="y",
        confidence=0.5,
        decision_gain=decision_gain,
    )


def test_empty_gain_fails():
    assert evaluate_decision_gain(_cand("")) is False


def test_null_markers_fail():
    for marker in ["없음", "None", "N/A", "-", "해당없음"]:
        assert evaluate_decision_gain(_cand(marker)) is False, marker


def test_too_short_fails():
    assert evaluate_decision_gain(_cand("예")) is False
    assert evaluate_decision_gain(_cand("y")) is False


def test_meaningful_gain_passes():
    assert evaluate_decision_gain(
        _cand("다른 rule set 적용 필요")
    ) is True
    assert evaluate_decision_gain(
        _cand("EXCLUDE 조건 추가로 예외 처리 가능")
    ) is True