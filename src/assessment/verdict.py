"""Final 4-state verdict (v0.2 10장).

입력: rule 이름 -> (effect, result) 매핑
출력: APPLICABLE / NOT_APPLICABLE / EXCLUDED / INDETERMINATE
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


def final_verdict(rule_results: list[RuleResult]) -> Verdict:
    """v0.2 10장 알고리즘."""
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

    # 4) 나머지 -> NOT_APPLICABLE
    return Verdict.NOT_APPLICABLE