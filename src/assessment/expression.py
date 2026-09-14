"""Expression tree evaluation (recursive).

rule.expression 테이블 구조를 그대로 반영.

    ExpressionTree = Node
    Node:
        expr_type: "AND" | "OR" | "NOT" | "PREDICATE"
        children: list[Node]        # AND/OR
        child: Node | None          # NOT (단항)
        predicate: Predicate | None # PREDICATE
        sort_order: int

v0.2 7.3 표현을 그대로 재귀 평가.
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

    # NOT은 children[0] 하나만 사용
    def __post_init__(self):
        if self.expr_type not in ("AND", "OR", "NOT", "PREDICATE"):
            raise ValueError(f"bad expr_type: {self.expr_type}")
        if self.expr_type == "PREDICATE" and self.predicate is None:
            raise ValueError("PREDICATE node requires predicate")
        if self.expr_type in ("AND", "OR") and not self.children:
            raise ValueError(f"{self.expr_type} node requires at least one child")
        if self.expr_type == "NOT" and len(self.children) != 1:
            raise ValueError("NOT node requires exactly one child")


def evaluate_tree(node: Node, facts: dict[str, Any]) -> TruthValue:
    """재귀 평가."""
    if node.expr_type == "PREDICATE":
        assert node.predicate is not None
        return evaluate_predicate(node.predicate, facts)

    if node.expr_type == "AND":
        results = [evaluate_tree(c, facts) for c in _sorted(node.children)]
        return t_and(*results)

    if node.expr_type == "OR":
        results = [evaluate_tree(c, facts) for c in _sorted(node.children)]
        return t_or(*results)

    if node.expr_type == "NOT":
        return t_not(evaluate_tree(node.children[0], facts))

    raise ValueError(f"unreachable: {node.expr_type}")


def _sorted(children: list[Node]) -> list[Node]:
    return sorted(children, key=lambda n: n.sort_order)