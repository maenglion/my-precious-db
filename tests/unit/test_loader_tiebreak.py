"""Grok #4: loader와 eval의 children 정렬 키가 일치해야 한다."""

from src.assessment.expression import evaluate_tree_with_trace
from src.assessment.loader import rows_to_tree


def row(expr_id, parent, expr_type, *, fact_key=None, operator=None,
        compare_value=None, sort_order=0):
    return {
        "expr_id": expr_id,
        "parent_expr_id": parent,
        "expr_type": expr_type,
        "bool_op": None,
        "fact_key": fact_key,
        "operator": operator,
        "compare_value": compare_value,
        "unit": None,
        "sort_order": sort_order,
    }


class TestLoaderTieBreakMatchesEval:
    def test_tie_break_by_expr_id_in_node_children(self):
        # 두 leaf 같은 sort_order=0, rows 삽입 순서는 b -> a
        rows = [
            row("root", None, "AND"),
            row("b", "root", "PREDICATE",
                fact_key="b", operator="=", compare_value=2, sort_order=0),
            row("a", "root", "PREDICATE",
                fact_key="a", operator="=", compare_value=1, sort_order=0),
        ]
        tree = rows_to_tree(rows)
        # loader가 (sort_order, expr_id) 로 정렬 -> ["a", "b"]
        assert [c.expr_id for c in tree.children] == ["a", "b"]

    def test_node_children_order_equals_trace_order(self):
        rows = [
            row("root", None, "AND"),
            row("b", "root", "PREDICATE",
                fact_key="b", operator="=", compare_value=2, sort_order=0),
            row("a", "root", "PREDICATE",
                fact_key="a", operator="=", compare_value=1, sort_order=0),
        ]
        tree = rows_to_tree(rows)
        _, traces = evaluate_tree_with_trace(tree, {"a": 1, "b": 2})
        node_order = [c.expr_id for c in tree.children]
        trace_order = [t.expr_id for t in traces]
        assert node_order == trace_order