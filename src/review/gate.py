"""Decision gain gate (DL-012).

분리했을 때 판정이 실제로 달라지는가?
- 다른 rule set / EXCLUDE / threshold / scope 중 하나라도 YES → 통과
- 전부 NO → 노드 아님 (alias/mapping으로 종결)

MVP: LLM이 명시한 decision_gain 필드의 유무로 판단.
TODO(013N): rules/excludes/thresholds 테이블과 실제 교차검증.
"""

from __future__ import annotations

from src.review.candidate import Candidate


_NULL_GAIN_MARKERS = frozenset({
    "",
    "없음",
    "none",
    "n/a",
    "na",
    "-",
    "해당없음",
})


def evaluate_decision_gain(candidate: Candidate) -> bool:
    """이 후보가 판정을 바꾸는가?

    Returns:
        True  → 승격 가치 있음 (사람 검수 큐로)
        False → 판정 안 바뀜 (승격해도 의미 없음)
    """
    gain = (candidate.decision_gain or "").strip().lower()
    if gain in _NULL_GAIN_MARKERS:
        return False
    if len(gain) < 5:
        return False
    return True