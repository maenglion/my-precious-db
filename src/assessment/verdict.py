"""Final 4-state verdict (v0.2 10장 + DL-003)."""

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
    effect: str
    result: TruthValue


def final_verdict(
    rule_results: list[RuleResult],
    *,
    candidate_scope_resolved: bool,
) -> Verdict:
    if not candidate_scope_resolved:
        return Verdict.INDETERMINATE

    include_results = [r for r in rule_results if r.effect == "INCLUDE"]
    exclude_results = [r for r in rule_results if r.effect == "EXCLUDE"]

    include_true = any(r.result is TruthValue.TRUE for r in include_results)
    include_unknown = any(r.result is TruthValue.UNKNOWN for r in include_results)
    exclude_true = any(r.result is TruthValue.TRUE for r in exclude_results)
    exclude_unknown = any(r.result is TruthValue.UNKNOWN for r in exclude_results)

    if include_true:
        if exclude_true:
            return Verdict.EXCLUDED
        if exclude_unknown:
            return Verdict.INDETERMINATE
        return Verdict.APPLICABLE

    if include_unknown:
        return Verdict.INDETERMINATE

    return Verdict.NOT_APPLICABLE