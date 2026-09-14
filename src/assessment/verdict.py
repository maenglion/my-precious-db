"""Final 4-state verdict (v0.2 10장).

알고리즘 (candidate_scope_resolved=True 일 때):
    IF any EXCLUDE rule == TRUE -> EXCLUDED
    ELSE IF any INCLUDE rule == TRUE -> APPLICABLE
    ELSE IF any relevant rule contains UNKNOWN -> INDETERMINATE
    ELSE -> NOT_APPLICABLE

Coverage safety (v0.2 12.1 RULE_COVERAGE):
    candidate_scope_resolved=False
    -> INDETERMINATE  (호출자는 residual_type='RULE_COVERAGE' 기록)

    이유: rule seed 누락 / 매핑 실패 / 버전 오류로 rule을 하나도
    못 가져온 경우 NOT_APPLICABLE로 확정하면 법률 시스템에서
    가장 위험한 false negative가 된다. 사람 검토로 돌린다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.assessment.logic import TruthValue


class Verdict(str, Enum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    EXCLUDED = "EXCLUDED"
    INDETERMINATE = "INDETERMINATE"


@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    name: str
    effect: str      # INCLUDE | EXCLUDE
    result: TruthValue


def final_verdict(
    rule_results: list[RuleResult],
    *,
    candidate_scope_resolved: bool,
) -> Verdict:
    """v0.2 10장 + 12.1 coverage 안전장치.

    Args:
        rule_results: 로딩된 rule들의 평가 결과.
        candidate_scope_resolved:
            True  - 후보 rule 스코프를 확정했음 (매칭 0건도 신뢰 가능)
            False - 스코프 불확실 (seed 누락/매핑 실패 등)
    """
    # 0) Coverage가 불확실하면 어떤 rule 결과도 최종 판정으로 승격하지 않는다.
    if not candidate_scope_resolved:
        return Verdict.INDETERMINATE

    # 1) EXCLUDE TRUE -> EXCLUDED
    for rr in rule_results:
        if rr.effect == "EXCLUDE" and rr.result is TruthValue.TRUE:
            return Verdict.EXCLUDED

    # 2) INCLUDE TRUE -> APPLICABLE
    for rr in rule_results:
        if rr.effect == "INCLUDE" and rr.result is TruthValue.TRUE:
            return Verdict.APPLICABLE

    # 3) UNKNOWN 포함 -> INDETERMINATE
    for rr in rule_results:
        if rr.result is TruthValue.UNKNOWN:
            return Verdict.INDETERMINATE

    # 4) 스코프 확정 + 매칭 0 또는 전부 FALSE -> NOT_APPLICABLE
    return Verdict.NOT_APPLICABLE