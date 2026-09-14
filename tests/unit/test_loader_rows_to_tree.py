"""rows_to_tree 유닛 테스트 (DB 불필요)."""

import pytest

from src.assessment.expression import evaluate_tree
from src.assessment.loader import rows_to_tree
from src.assessment.logic import TruthValue

T = TruthValue.TRUE
F = TruthValue.FALSE
U = TruthValue.UNKNOWN


def row(expr_id, parent, expr_type, *, fact_key=None, operator=None,
        compare_value=None, unit=None, sort_order=0):
    return {
        "expr_id": expr_id,
        "parent_expr_id": parent,
        "expr_type": expr_type,
        "bool_op": None,
        "fact_key": fact_key,
        "operator": operator,
        "compare_value": compare_value,
        "unit": unit,
        "sort_order": sort_order,
    }


class TestSimplePredicate:
    def test_single_leaf(self):
        rows = [row("e1", None, "PREDICATE",
                    fact_key="area", operator=">=", compare_value=3000)]
        tree = rows_to_tree(rows)
        assert evaluate_tree(tree, {"area": 3500}) is T


class TestOrMedical:
    def test_or_two_leaves(self):
        rows = [
            row("root", None, "OR", sort_order=0),
            row("a", "root", "PREDICATE",
                fact_key="area", operator=">=", compare_value=2000, sort_order=0),
            row("b", "root", "PREDICATE",
                fact_key="beds", operator=">=", compare_value=100, sort_order=1),
        ]
        tree = rows_to_tree(rows)
        assert evaluate_tree(tree, {"area": 3000}) is T
        assert evaluate_tree(tree, {"area": 1000, "beds": 50}) is F
        assert evaluate_tree(tree, {"area": 1000}) is U


class TestAndOfficetel:
    def test_and_two_leaves(self):
        rows = [
            row("root", None, "AND"),
            row("a", "root", "PREDICATE",
                fact_key="use_type", operator="=", compare_value="OFFICE", sort_order=0),
            row("b", "root", "PREDICATE",
                fact_key="subtype", operator="=", compare_value="OFFICETEL", sort_order=1),
        ]
        tree = rows_to_tree(rows)
        assert evaluate_tree(tree, {"use_type": "OFFICE", "subtype": "OFFICETEL"}) is T
        assert evaluate_tree(tree, {"use_type": "OFFICE"}) is U
        assert evaluate_tree(tree, {"use_type": "MEDICAL"}) is F


class TestNested:
    def test_not_or(self):
        rows = [
            row("root", None, "NOT"),
            row("or1", "root", "OR", sort_order=0),
            row("a", "or1", "PREDICATE",
                fact_key="area", operator=">=", compare_value=2000, sort_order=0),
            row("b", "or1", "PREDICATE",
                fact_key="beds", operator=">=", compare_value=100, sort_order=1),
        ]
        tree = rows_to_tree(rows)
        assert evaluate_tree(tree, {"area": 1000, "beds": 50}) is T
        assert evaluate_tree(tree, {"area": 3000}) is F


class TestSortOrderRespected:
    def test_order_of_children(self):
        rows = [
            row("root", None, "AND"),
            row("a", "root", "PREDICATE",
                fact_key="a", operator="=", compare_value=1, sort_order=5),
            row("b", "root", "PREDICATE",
                fact_key="b", operator="=", compare_value=2, sort_order=1),
        ]
        tree = rows_to_tree(rows)
        assert tree.children[0].predicate.fact_key == "b"
        assert tree.children[1].predicate.fact_key == "a"


class TestValidation:
    def test_empty(self):
        with pytest.raises(ValueError):
            rows_to_tree([])

    def test_multiple_roots(self):
        rows = [
            row("r1", None, "PREDICATE", fact_key="a", operator="=", compare_value=1),
            row("r2", None, "PREDICATE", fact_key="b", operator="=", compare_value=2),
        ]
        with pytest.raises(ValueError):
            rows_to_tree(rows)