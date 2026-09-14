"""DB -> Expression tree 로더.

rule.rule + rule.expression을 읽어 Node 트리로 변환.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.assessment.expression import Node
from src.assessment.predicate import Predicate


@dataclass(frozen=True)
class LoadedRule:
    rule_id: str
    name: str
    effect: str
    priority: int
    source_node_id: str
    root: Node


def rows_to_tree(rows: list[dict]) -> Node:
    """rule.expression 행 목록 -> Node 트리.

    rows는 하나의 rule에 속한 모든 expression.
    """
    if not rows:
        raise ValueError("no expression rows")

    by_id: dict[str, dict] = {str(r["expr_id"]): r for r in rows}
    children: dict[str | None, list[str]] = {}
    for expr_id, row in by_id.items():
        parent = row.get("parent_expr_id")
        parent_key = str(parent) if parent else None
        children.setdefault(parent_key, []).append(expr_id)

    for key in children:
        children[key].sort(key=lambda eid: by_id[eid].get("sort_order", 0))

    roots = children.get(None, [])
    if len(roots) != 1:
        raise ValueError(
            f"expected exactly one root expression, found {len(roots)}"
        )

    def build(expr_id: str) -> Node:
        row = by_id[expr_id]
        expr_type = row["expr_type"]
        if expr_type == "PREDICATE":
            pred = Predicate(
                fact_key=row["fact_key"],
                operator=row["operator"],
                compare_value=row["compare_value"],
                unit=row.get("unit"),
            )
            return Node(expr_type="PREDICATE", predicate=pred,
                        sort_order=row.get("sort_order", 0))
        child_nodes = [build(cid) for cid in children.get(expr_id, [])]
        return Node(expr_type=expr_type, children=child_nodes,
                    sort_order=row.get("sort_order", 0))

    return build(roots[0])