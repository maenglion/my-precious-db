"""Predicate 평가 테스트."""

from src.assessment.logic import TruthValue
from src.assessment.predicate import Predicate, evaluate_predicate

T = TruthValue.TRUE
F = TruthValue.FALSE
U = TruthValue.UNKNOWN


class TestNumericOperators:
    def test_ge_true(self):
        p = Predicate("area", ">=", 3000)
        assert evaluate_predicate(p, {"area": 3500}) is T

    def test_ge_equal_boundary(self):
        p = Predicate("area", ">=", 3000)
        assert evaluate_predicate(p, {"area": 3000}) is T

    def test_ge_false(self):
        p = Predicate("area", ">=", 3000)
        assert evaluate_predicate(p, {"area": 2999}) is F

    def test_le(self):
        p = Predicate("area", "<=", 1000)
        assert evaluate_predicate(p, {"area": 1000}) is T
        assert evaluate_predicate(p, {"area": 1001}) is F

    def test_gt(self):
        p = Predicate("beds", ">", 100)
        assert evaluate_predicate(p, {"beds": 101}) is T
        assert evaluate_predicate(p, {"beds": 100}) is F

    def test_lt(self):
        p = Predicate("floor", "<", 5)
        assert evaluate_predicate(p, {"floor": 4}) is T
        assert evaluate_predicate(p, {"floor": 5}) is F


class TestEquality:
    def test_eq_string(self):
        p = Predicate("use_type", "=", "OFFICE")
        assert evaluate_predicate(p, {"use_type": "OFFICE"}) is T
        assert evaluate_predicate(p, {"use_type": "MEDICAL"}) is F

    def test_ne(self):
        p = Predicate("subtype", "!=", "OFFICETEL")
        assert evaluate_predicate(p, {"subtype": "GENERAL"}) is T
        assert evaluate_predicate(p, {"subtype": "OFFICETEL"}) is F

    def test_eq_bool(self):
        p = Predicate("is_officetel", "=", False)
        assert evaluate_predicate(p, {"is_officetel": False}) is T
        assert evaluate_predicate(p, {"is_officetel": True}) is F


class TestUnknown:
    def test_missing_fact(self):
        p = Predicate("beds", ">=", 100)
        assert evaluate_predicate(p, {}) is U

    def test_type_mismatch(self):
        p = Predicate("area", ">=", 3000)
        # area가 문자열이면 비교 불가
        assert evaluate_predicate(p, {"area": "big"}) is U

    def test_missing_other_fact_still_ok(self):
        p = Predicate("area", ">=", 3000)
        assert evaluate_predicate(p, {"area": 3500, "beds": 50}) is T


class TestUnknownOperator:
    def test_bad_operator(self):
        p = Predicate("area", "~=", 3000)
        try:
            evaluate_predicate(p, {"area": 3500})
            assert False, "should raise"
        except ValueError:
            pass