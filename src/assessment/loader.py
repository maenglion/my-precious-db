"""DB -> Expression tree 로더.

rule.expression row -> Node 트리.
expr_id는 AND/OR/NOT/PREDICATE 모든 노드에 보존된다.
children 정렬은 (sort_order, expr_id) — eval의 _sorted와 동일 키.
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
    if not rows:
        raise ValueError("no expression rows")

    by_id: dict[str, dict] = {str(r["expr_id"]): r for r in rows}
    children: dict[str | None, list[str]] = {}
    for expr_id, row in by_id.items():
        parent = row.get("parent_expr_id")
        parent_key = str(parent) if parent else None
        children.setdefault(parent_key, []).append(expr_id)

    for key in children:
        # eval의 _sorted와 동일 키: (sort_order, expr_id)
        children[key].sort(
            key=lambda eid: (by_id[eid].get("sort_order", 0), eid)
        )

    roots = children.get(None, [])
    if len(roots) != 1:
        raise ValueError(
            f"expected exactly one root expression, found {len(roots)}"
        )

    def build(expr_id: str) -> Node:
        row = by_id[expr_id]
        expr_type = row["expr_type"]
        sort_order = row.get("sort_order", 0)
        if expr_type == "PREDICATE":
            pred = Predicate(
                fact_key=row["fact_key"],
                operator=row["operator"],
                compare_value=row["compare_value"],
                unit=row.get("unit"),
            )
            return Node(expr_type="PREDICATE", predicate=pred,
                        sort_order=sort_order, expr_id=expr_id)
        child_nodes = [build(cid) for cid in children.get(expr_id, [])]
        return Node(expr_type=expr_type, children=child_nodes,
                    sort_order=sort_order, expr_id=expr_id)

    return build(roots[0])