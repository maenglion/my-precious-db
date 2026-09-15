"""Predicate evaluation.

fact_key / operator / compare_value 로 개별 조건을 평가.
fact가 없으면 UNKNOWN (v0.2 9장).

operator: =, !=, >, >=, <, <=
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.assessment.logic import TruthValue


@dataclass(frozen=True)
class Predicate:
    fact_key: str
    operator: str
    compare_value: Any
    unit: str | None = None


def evaluate_predicate(
    predicate: Predicate,
    facts: dict[str, Any],
) -> TruthValue:
    """fact_key가 facts에 없거나 None이면 UNKNOWN.

    bool <-> number 혼용은 UNKNOWN (값 오염 방지).
    """
    if predicate.fact_key not in facts:
        return TruthValue.UNKNOWN

    actual = facts[predicate.fact_key]
    if actual is None:
        return TruthValue.UNKNOWN

    expected = predicate.compare_value

    # bool <-> number 혼용 거부
    if isinstance(actual, bool) != isinstance(expected, bool):
        return TruthValue.UNKNOWN

    try:
        return _apply(predicate.operator, actual, expected)
    except TypeError:
        return TruthValue.UNKNOWN


def _apply(op: str, actual: Any, expected: Any) -> TruthValue:
    if op == "=":
        return _tv(actual == expected)
    if op == "!=":
        return _tv(actual != expected)
    if op == ">":
        return _tv(actual > expected)
    if op == ">=":
        return _tv(actual >= expected)
    if op == "<":
        return _tv(actual < expected)
    if op == "<=":
        return _tv(actual <= expected)
    raise ValueError(f"unknown operator: {op}")


def _tv(b: bool) -> TruthValue:
    return TruthValue.TRUE if b else TruthValue.FALSE