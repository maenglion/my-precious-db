"""Predicate evaluation.

fact_key / operator / compare_value 로 개별 조건을 평가.
fact가 없으면 UNKNOWN (v0.2 9장).

operator:
    =, !=, >, >=, <, <=
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
    """fact_key가 facts에 없으면 UNKNOWN.

    value_json이 리스트/딕셔너리면 그대로 비교.
    타입 미스매치는 UNKNOWN.
    """
    if predicate.fact_key not in facts:
        return TruthValue.UNKNOWN

    actual = facts[predicate.fact_key]
    expected = predicate.compare_value

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