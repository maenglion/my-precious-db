"""Predicate trace 테스트 (Ticket 012c)."""

import pytest

from src.assessment.expression import (
    Node,
    PredicateTrace,
    evaluate_tree,
    evaluate_tree_with_trace,
)
from src.assessment.loader import rows_to_tree
from src.assessment.logic import TruthValue
from src.assessment.predicate import Predicate

T = TruthValue.TRUE
F = TruthValue.FALSE
U = TruthValue.UNKNOWN


def leaf(fact_key, op, val, *, expr_id=None, sort_order=0):
    return Node(
        expr_type="PREDICATE",
        predicate=Predicate(fact_key, op, val),
        expr_id=expr_id,
        sort_order=sort_order,
    )


# ---------- 1~4: 단일 leaf ----------

class TestSingleTrace:
    def test_true_trace(self):
        tree = leaf("area", ">=", 3000, expr_id="e1")
        result, traces = evaluate_tree_with_trace(tree, {"area": 3500})
        assert result is T
        assert len(traces) == 1
        t = traces[0]
        assert t.expr_id == "e1"
        assert t.fact_key == "area"
        assert t.actual_value == 3500
        assert t.expected_value == 3000
        assert t.operator == ">="
        assert t.result is T
        assert t.reason is None
        assert t.fact_id is None

    def test_false_trace(self):
        tree = leaf("area", ">=", 3000, expr_id="e1")
        result, traces = evaluate_tree_with_trace(tree, {"area": 2500})
        assert result is F
        assert len(traces) == 1
        assert traces[0].result is F
        assert traces[0].reason is None

    def test_missing_fact_unknown(self):
        tree = leaf("beds", ">=", 100, expr_id="e1")
        result, traces = evaluate_tree_with_trace(tree, {})
        assert result is U
        t = traces[0]
        assert t.result is U
        assert t.reason == "MISSING_FACT"
        assert t.actual_value is None
        assert t.fact_id is None

    def test_type_mismatch_unknown(self):
        tree = leaf("area", ">=", 3000, expr_id="e1")
        result, traces = evaluate_tree_with_trace(tree, {"area": "big"})
        assert result is U
        t = traces[0]
        assert t.result is U
        assert t.reason == "TYPE_MISMATCH"
        assert t.actual_value == "big"


# ---------- 5~7: 트리 trace 개수/순서 ----------

class TestTreeTraces:
    def test_or_two_leaves_two_traces(self):
        tree = Node(
            expr_type="OR",
            expr_id="root",
            children=[
                leaf("area", ">=", 2000, expr_id="a", sort_order=0),
                leaf("beds", ">=", 100, expr_id="b", sort_order=1),
            ],
        )
        result, traces = evaluate_tree_with_trace(tree, {"area": 3000})
        assert result is T
        assert len(traces) == 2
        assert traces[0].expr_id == "a"
        assert traces[1].expr_id == "b"

    def test_nested_not_and_all_leaves(self):
        # NOT (A AND B)
        tree = Node(
            expr_type="NOT",
            expr_id="root",
            children=[
                Node(
                    expr_type="AND",
                    expr_id="and1",
                    children=[
                        leaf("use_type", "=", "OFFICE", expr_id="a", sort_order=0),
                        leaf("subtype", "=", "OFFICETEL", expr_id="b", sort_order=1),
                    ],
                ),
            ],
        )
        result, traces = evaluate_tree_with_trace(
            tree, {"use_type": "OFFICE", "subtype": "GENERAL"}
        )
        assert result is T
        assert len(traces) == 2
        assert {t.expr_id for t in traces} == {"a", "b"}

    def test_sort_order_determines_trace_order(self):
        tree = Node(
            expr_type="AND",
            children=[
                leaf("a", "=", 1, expr_id="ea", sort_order=5),
                leaf("b", "=", 2, expr_id="eb", sort_order=1),
            ],
        )
        _, traces = evaluate_tree_with_trace(tree, {"a": 1, "b": 2})
        assert traces[0].expr_id == "eb"
        assert traces[1].expr_id == "ea"


# ---------- 8~9: loader expr_id 보존 ----------

class TestLoaderPreservesExprId:
    def _rows(self):
        return [
            {"expr_id": "root", "parent_expr_id": None, "expr_type": "OR",
             "bool_op": None, "fact_key": None, "operator": None,
             "compare_value": None, "unit": None, "sort_order": 0},
            {"expr_id": "a", "parent_expr_id": "root", "expr_type": "PREDICATE",
             "bool_op": None, "fact_key": "area", "operator": ">=",
             "compare_value": 2000, "unit": None, "sort_order": 0},
            {"expr_id": "b", "parent_expr_id": "root", "expr_type": "PREDICATE",
             "bool_op": None, "fact_key": "beds", "operator": ">=",
             "compare_value": 100, "unit": None, "sort_order": 1},
        ]

    def test_root_expr_id_preserved(self):
        tree = rows_to_tree(self._rows())
        assert tree.expr_id == "root"
        assert tree.expr_type == "OR"

    def test_child_expr_ids_preserved(self):
        tree = rows_to_tree(self._rows())
        assert [c.expr_id for c in tree.children] == ["a", "b"]


# ---------- 10~11: fact_meta ----------

class TestFactMeta:
    def test_fact_id_preserved(self):
        meta = {"area": {"fact_id": "uuid-1", "value": 3500, "unit": "㎡"}}
        tree = leaf("area", ">=", 3000, expr_id="e1")
        _, traces = evaluate_tree_with_trace(tree, {"area": 3500}, fact_meta=meta)
        assert traces[0].fact_id == "uuid-1"

    def test_fact_meta_optional(self):
        tree = leaf("area", ">=", 3000, expr_id="e1")
        result, traces = evaluate_tree_with_trace(tree, {"area": 3500})
        assert result is T
        assert traces[0].fact_id is None

    def test_facts_is_source_of_truth(self):
        # fact_meta.value가 달라도 판정값은 facts 사용
        meta = {"area": {"fact_id": "uuid-1", "value": 99999}}
        tree = leaf("area", ">=", 3000, expr_id="e1")
        result, traces = evaluate_tree_with_trace(
            tree, {"area": 3500}, fact_meta=meta
        )
        assert result is T
        assert traces[0].actual_value == 3500

    def test_fact_meta_missing_fact_id(self):
        meta = {"area": {}}  # fact_id 없음
        tree = leaf("area", ">=", 3000, expr_id="e1")
        _, traces = evaluate_tree_with_trace(tree, {"area": 3500}, fact_meta=meta)
        assert traces[0].fact_id is None


# ---------- 12: API 호환 ----------

class TestAPICompat:
    def test_evaluate_tree_matches_with_trace(self):
        tree = Node(
            expr_type="OR",
            children=[
                leaf("area", ">=", 2000, sort_order=0),
                leaf("beds", ">=", 100, sort_order=1),
            ],
        )
        cases = [
            {"area": 3000},
            {"area": 1000, "beds": 50},
            {"area": 1000},
            {},
            {"area": "big"},
        ]
        for facts in cases:
            r1 = evaluate_tree(tree, facts)
            r2, _ = evaluate_tree_with_trace(tree, facts)
            assert r1 is r2

    def test_unknown_operator_still_raises(self):
        # programmer/config error -> ValueError 유지
        tree = leaf("area", "~=", 3000)
        with pytest.raises(ValueError):
            evaluate_tree_with_trace(tree, {"area": 3500})
        with pytest.raises(ValueError):
            evaluate_tree(tree, {"area": 3500})