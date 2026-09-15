"""Grok 반증감사 (Ticket 012c) 회귀 테스트.

FP/FN 중 수용한 항목을 고정한다.
"""

import pytest

from src.assessment.expression import (
    Node,
    evaluate_tree,
    evaluate_tree_with_trace,
)
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


# ----- FP-1: Kleene OR + 결측 = TRUE (수용 아님, 명시적 고정) -----

class TestFP1_KleeneOrWithMissing:
    def test_or_with_missing_is_true(self):
        tree = Node(expr_type="OR", children=[
            leaf("area", ">=", 2000, sort_order=0),
            leaf("beds", ">=", 100, sort_order=1),
        ])
        result, traces = evaluate_tree_with_trace(tree, {"area": 3000})
        assert result is T  # v0.2 §9.2 TRUE ∨ UNKNOWN = TRUE
        assert traces[1].reason == "MISSING_FACT"


# ----- FP-2: None -> NULL_VALUE -----

class TestFP2_NullValue:
    def test_none_value_gets_null_reason(self):
        tree = leaf("area", ">=", 3000, expr_id="e1")
        result, traces = evaluate_tree_with_trace(tree, {"area": None})
        assert result is U
        assert traces[0].reason == "NULL_VALUE"
        assert traces[0].actual_value is None

    def test_missing_key_still_missing_fact(self):
        tree = leaf("area", ">=", 3000, expr_id="e1")
        _, traces = evaluate_tree_with_trace(tree, {})
        assert traces[0].reason == "MISSING_FACT"


# ----- FP-5: bool <-> number 혼용 거부 -----

class TestFP5_BoolNumericMix:
    def test_bool_actual_vs_number_expected(self):
        tree = leaf("area", ">=", 1, expr_id="e1")
        result, traces = evaluate_tree_with_trace(tree, {"area": True})
        assert result is U
        assert traces[0].reason == "TYPE_MISMATCH"

    def test_number_actual_vs_bool_expected(self):
        tree = leaf("flag", "=", True, expr_id="e1")
        result, traces = evaluate_tree_with_trace(tree, {"flag": 1})
        assert result is U
        assert traces[0].reason == "TYPE_MISMATCH"

    def test_bool_vs_bool_ok(self):
        tree = leaf("flag", "=", True, expr_id="e1")
        result, _ = evaluate_tree_with_trace(tree, {"flag": True})
        assert result is T


# ----- FP-4: fact_meta 오염 (dict 아니면 버림) -----

class TestFP4_FactMetaContamination:
    def test_string_fact_meta_does_not_crash(self):
        tree = leaf("area", ">=", 3000, expr_id="e1")
        result, traces = evaluate_tree_with_trace(
            tree, {"area": 3500}, fact_meta={"area": "uuid-1"}
        )
        assert result is T  # 판정은 facts SoT
        assert traces[0].fact_id is None  # 오염된 meta는 버림

    def test_list_fact_meta_does_not_crash(self):
        tree = leaf("area", ">=", 3000, expr_id="e1")
        result, traces = evaluate_tree_with_trace(
            tree, {"area": 3500}, fact_meta={"area": ["uuid-1"]}
        )
        assert result is T
        assert traces[0].fact_id is None

    def test_none_fact_meta_ok(self):
        tree = leaf("area", ">=", 3000, expr_id="e1")
        result, traces = evaluate_tree_with_trace(
            tree, {"area": 3500}, fact_meta=None
        )
        assert result is T
        assert traces[0].fact_id is None


# ----- FN-5: sort_order 동률 -> expr_id tie-break -----

class TestFN5_SortOrderTieBreak:
    def test_tie_break_by_expr_id(self):
        # 두 leaf 같은 sort_order=0, expr_id "b" < "a" 순서 아님 -> "a"가 먼저
        a = leaf("a", "=", 1, expr_id="a", sort_order=0)
        b = leaf("b", "=", 2, expr_id="b", sort_order=0)
        tree = Node(expr_type="AND", children=[b, a])  # 입력 순서 반대
        _, traces = evaluate_tree_with_trace(tree, {"a": 1, "b": 2})
        assert traces[0].expr_id == "a"
        assert traces[1].expr_id == "b"

    def test_tie_break_deterministic(self):
        a = leaf("a", "=", 1, expr_id="a", sort_order=0)
        b = leaf("b", "=", 2, expr_id="b", sort_order=0)
        t1 = Node(expr_type="AND", children=[a, b])
        t2 = Node(expr_type="AND", children=[b, a])
        _, tr1 = evaluate_tree_with_trace(t1, {"a": 1, "b": 2})
        _, tr2 = evaluate_tree_with_trace(t2, {"a": 1, "b": 2})
        assert [t.expr_id for t in tr1] == [t.expr_id for t in tr2]


# ----- FN-1 / X-2: unknown operator는 여전히 ValueError -----

class TestFN1_UnknownOperatorStillRaises:
    def test_unknown_operator_mid_leaf_raises(self):
        # fail-fast 유지. programmer/config error는 조용히 넘기지 않는다.
        tree = Node(expr_type="AND", children=[
            leaf("area", ">=", 2000, expr_id="a", sort_order=0),
            leaf("beds", "~=", 100, expr_id="b", sort_order=1),
        ])
        with pytest.raises(ValueError):
            evaluate_tree_with_trace(tree, {"area": 3000, "beds": 50})

    def test_predicate_direct_still_raises(self):
        tree = leaf("area", "~=", 3000, expr_id="e1")
        with pytest.raises(ValueError):
            evaluate_tree(tree, {"area": 3500})


# ----- API 호환 -----

class TestAPIStillHolds:
    def test_evaluate_tree_equals_with_trace(self):
        tree = Node(expr_type="OR", children=[
            leaf("area", ">=", 2000, sort_order=0),
            leaf("beds", ">=", 100, sort_order=1),
        ])
        for facts in [
            {"area": 3000},
            {"area": 1000, "beds": 50},
            {"area": 1000},
            {},
            {"area": None},
            {"area": True},
        ]:
            r1 = evaluate_tree(tree, facts)
            r2, _ = evaluate_tree_with_trace(tree, facts)
            assert r1 is r2