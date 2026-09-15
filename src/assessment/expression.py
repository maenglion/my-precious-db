"""Expression tree evaluation + predicate trace.

- evaluate_tree(node, facts) -> TruthValue
- evaluate_tree_with_trace(node, facts, fact_meta=None)
    -> (TruthValue, list[PredicateTrace])

fact_meta는 provenance/logging 용도. dict가 아니면 버린다.
판정 실제값의 source of truth는 facts dict.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.assessment.logic import TruthValue, t_and, t_not, t_or
from src.assessment.predicate import Predicate, evaluate_predicate


@dataclass
class Node:
    expr_type: str
    predicate: Predicate | None = None
    children: list["Node"] = field(default_factory=list)
    sort_order: int = 0
    expr_id: str | None = None

    def __post_init__(self):
        if self.expr_type not in ("AND", "OR", "NOT", "PREDICATE"):
            raise ValueError(f"bad expr_type: {self.expr_type}")
        if self.expr_type == "PREDICATE" and self.predicate is None:
            raise ValueError("PREDICATE node requires predicate")
        if self.expr_type in ("AND", "OR") and not self.children:
            raise ValueError(f"{self.expr_type} node requires at least one child")
        if self.expr_type == "NOT" and len(self.children) != 1:
            raise ValueError("NOT node requires exactly one child")


@dataclass(frozen=True)
class PredicateTrace:
    expr_id: str | None
    fact_key: str
    fact_id: str | None
    actual_value: Any
    expected_value: Any
    operator: str
    result: TruthValue
    reason: str | None
    # reason: None | MISSING_FACT | NULL_VALUE | TYPE_MISMATCH


def evaluate_tree(node: Node, facts: dict[str, Any]) -> TruthValue:
    result, _ = evaluate_tree_with_trace(node, facts, None)
    return result


def evaluate_tree_with_trace(
    node: Node,
    facts: dict[str, Any],
    fact_meta: dict[str, dict] | None = None,
) -> tuple[TruthValue, list[PredicateTrace]]:
    traces: list[PredicateTrace] = []

    def visit(n: Node) -> TruthValue:
        if n.expr_type == "PREDICATE":
            return _eval_leaf(n, facts, fact_meta, traces)
        if n.expr_type == "AND":
            results = [visit(c) for c in _sorted(n.children)]
            return t_and(*results)
        if n.expr_type == "OR":
            results = [visit(c) for c in _sorted(n.children)]
            return t_or(*results)
        if n.expr_type == "NOT":
            return t_not(visit(n.children[0]))
        raise ValueError(f"unreachable: {n.expr_type}")

    result = visit(node)
    return result, traces


def _eval_leaf(
    node: Node,
    facts: dict[str, Any],
    fact_meta: dict[str, dict] | None,
    traces: list[PredicateTrace],
) -> TruthValue:
    assert node.predicate is not None
    p = node.predicate

    raw = (fact_meta or {}).get(p.fact_key)
    meta = raw if isinstance(raw, dict) else {}
    fact_id = meta.get("fact_id")

    # fact_key 없음
    if p.fact_key not in facts:
        traces.append(PredicateTrace(
            expr_id=node.expr_id,
            fact_key=p.fact_key,
            fact_id=fact_id,
            actual_value=None,
            expected_value=p.compare_value,
            operator=p.operator,
            result=TruthValue.UNKNOWN,
            reason="MISSING_FACT",
        ))
        return TruthValue.UNKNOWN

    actual = facts[p.fact_key]

    # 값이 None
    if actual is None:
        traces.append(PredicateTrace(
            expr_id=node.expr_id,
            fact_key=p.fact_key,
            fact_id=fact_id,
            actual_value=None,
            expected_value=p.compare_value,
            operator=p.operator,
            result=TruthValue.UNKNOWN,
            reason="NULL_VALUE",
        ))
        return TruthValue.UNKNOWN

    result = evaluate_predicate(p, facts)
    if result is TruthValue.UNKNOWN:
        reason = "TYPE_MISMATCH"
    else:
        reason = None

    traces.append(PredicateTrace(
        expr_id=node.expr_id,
        fact_key=p.fact_key,
        fact_id=fact_id,
        actual_value=actual,
        expected_value=p.compare_value,
        operator=p.operator,
        result=result,
        reason=reason,
    ))
    return result


def _sorted(children: list[Node]) -> list[Node]:
    # (sort_order, expr_id) tie-break: 순서 계약을 명시적으로 고정
    return sorted(children, key=lambda n: (n.sort_order, n.expr_id or ""))