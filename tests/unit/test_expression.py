"""Expression tree 테스트 — v0.2 7.3 예제 그대로."""

import pytest

from src.assessment.expression import Node, evaluate_tree
from src.assessment.logic import TruthValue
from src.assessment.predicate import Predicate

T = TruthValue.TRUE
F = TruthValue.FALSE
U = TruthValue.UNKNOWN


def p(fact_key, op, val):
    return Node(expr_type="PREDICATE", predicate=Predicate(fact_key, op, val))


class TestPredicateLeaf:
    def test_simple_true(self):
        tree = p("area", ">=", 3000)
        assert evaluate_tree(tree, {"area": 3500}) is T

    def test_simple_false(self):
        tree = p("area", ">=", 3000)
        assert evaluate_tree(tree, {"area": 2500}) is F

    def test_simple_unknown(self):
        tree = p("area", ">=", 3000)
        assert evaluate_tree(tree, {}) is U


class TestOrMedical:
    """v0.2 7.3: 의료기관 적용.

    OR
    ├─ area >= 2000
    └─ beds >= 100
    """

    def test_area_true(self):
        tree = Node(expr_type="OR", children=[
            p("area", ">=", 2000),
            p("beds", ">=", 100),
        ])
        assert evaluate_tree(tree, {"area": 3000}) is T

    def test_beds_true_area_false(self):
        tree = Node(expr_type="OR", children=[
            p("area", ">=", 2000),
            p("beds", ">=", 100),
        ])
        assert evaluate_tree(tree, {"area": 1000, "beds": 150}) is T

    def test_both_false(self):
        tree = Node(expr_type="OR", children=[
            p("area", ">=", 2000),
            p("beds", ">=", 100),
        ])
        assert evaluate_tree(tree, {"area": 1000, "beds": 50}) is F

    def test_area_false_beds_unknown(self):
        # T07 시나리오
        tree = Node(expr_type="OR", children=[
            p("area", ">=", 2000),
            p("beds", ">=", 100),
        ])
        assert evaluate_tree(tree, {"area": 1000}) is U

    def test_area_true_beds_unknown(self):
        # TRUE가 있으면 OR은 TRUE
        tree = Node(expr_type="OR", children=[
            p("area", ">=", 2000),
            p("beds", ">=", 100),
        ])
        assert evaluate_tree(tree, {"area": 3000}) is T


class TestAndOfficetel:
    """v0.2 7.3: 오피스텔 제외.

    AND
    ├─ use_type = OFFICE
    └─ subtype = OFFICETEL

    effect: EXCLUDE
    """

    def test_both_true(self):
        tree = Node(expr_type="AND", children=[
            p("use_type", "=", "OFFICE"),
            p("subtype", "=", "OFFICETEL"),
        ])
        assert evaluate_tree(tree, {"use_type": "OFFICE", "subtype": "OFFICETEL"}) is T

    def test_one_false(self):
        tree = Node(expr_type="AND", children=[
            p("use_type", "=", "OFFICE"),
            p("subtype", "=", "OFFICETEL"),
        ])
        assert evaluate_tree(tree, {"use_type": "OFFICE", "subtype": "GENERAL"}) is F

    def test_unknown_second(self):
        tree = Node(expr_type="AND", children=[
            p("use_type", "=", "OFFICE"),
            p("subtype", "=", "OFFICETEL"),
        ])
        assert evaluate_tree(tree, {"use_type": "OFFICE"}) is U

    def test_false_dominates_unknown(self):
        tree = Node(expr_type="AND", children=[
            p("use_type", "=", "OFFICE"),
            p("subtype", "=", "OFFICETEL"),
        ])
        assert evaluate_tree(tree, {"use_type": "MEDICAL"}) is F


class TestNot:
    def test_not_true(self):
        tree = Node(expr_type="NOT", children=[p("area", ">=", 3000)])
        assert evaluate_tree(tree, {"area": 2000}) is T

    def test_not_false(self):
        tree = Node(expr_type="NOT", children=[p("area", ">=", 3000)])
        assert evaluate_tree(tree, {"area": 4000}) is F

    def test_not_unknown(self):
        tree = Node(expr_type="NOT", children=[p("area", ">=", 3000)])
        assert evaluate_tree(tree, {}) is U


class TestNested:
    """중첩: NOT (A OR B)"""

    def test_not_or_all_false(self):
        tree = Node(expr_type="NOT", children=[
            Node(expr_type="OR", children=[
                p("area", ">=", 2000),
                p("beds", ">=", 100),
            ])
        ])
        assert evaluate_tree(tree, {"area": 1000, "beds": 50}) is T

    def test_not_or_one_true(self):
        tree = Node(expr_type="NOT", children=[
            Node(expr_type="OR", children=[
                p("area", ">=", 2000),
                p("beds", ">=", 100),
            ])
        ])
        assert evaluate_tree(tree, {"area": 3000, "beds": 50}) is F


class TestSortOrder:
    def test_children_evaluated_in_order(self):
        # 순서 상관없이 결과 동일
        t1 = Node(expr_type="AND", children=[
            Node(expr_type="PREDICATE", predicate=Predicate("a", "=", 1), sort_order=1),
            Node(expr_type="PREDICATE", predicate=Predicate("b", "=", 2), sort_order=0),
        ])
        t2 = Node(expr_type="AND", children=[
            Node(expr_type="PREDICATE", predicate=Predicate("a", "=", 1), sort_order=0),
            Node(expr_type="PREDICATE", predicate=Predicate("b", "=", 2), sort_order=1),
        ])
        facts = {"a": 1, "b": 2}
        assert evaluate_tree(t1, facts) is T
        assert evaluate_tree(t2, facts) is T


class TestValidation:
    def test_bad_expr_type(self):
        with pytest.raises(ValueError):
            Node(expr_type="XOR")

    def test_predicate_without_predicate(self):
        with pytest.raises(ValueError):
            Node(expr_type="PREDICATE")

    def test_and_without_children(self):
        with pytest.raises(ValueError):
            Node(expr_type="AND")

    def test_not_with_two_children(self):
        with pytest.raises(ValueError):
            Node(expr_type="NOT", children=[
                p("a", "=", 1),
                p("b", "=", 2),
            ])