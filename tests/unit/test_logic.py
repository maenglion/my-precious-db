"""Tests for 3-valued logic (v0.2 9장)."""

import pytest

from src.assessment.logic import TruthValue, t_and, t_not, t_or

T = TruthValue.TRUE
F = TruthValue.FALSE
U = TruthValue.UNKNOWN


class TestAnd:
    def test_all_true(self):
        assert t_and(T, T, T) is T

    def test_any_false_dominates(self):
        assert t_and(T, F, T) is F
        assert t_and(F, F, F) is F

    def test_false_beats_unknown(self):
        assert t_and(T, F, U) is F

    def test_unknown_when_no_false(self):
        assert t_and(T, U, T) is U
        assert t_and(U, U) is U

    def test_single_value(self):
        assert t_and(T) is T
        assert t_and(F) is F
        assert t_and(U) is U

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            t_and()


class TestOr:
    def test_all_false(self):
        assert t_or(F, F, F) is F

    def test_any_true_dominates(self):
        assert t_or(F, T, F) is T
        assert t_or(T, T, T) is T

    def test_true_beats_unknown(self):
        assert t_or(F, T, U) is T

    def test_unknown_when_no_true(self):
        assert t_or(F, U, F) is U
        assert t_or(U, U) is U

    def test_single_value(self):
        assert t_or(T) is T
        assert t_or(F) is F
        assert t_or(U) is U

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            t_or()


class TestNot:
    def test_true_to_false(self):
        assert t_not(T) is F

    def test_false_to_true(self):
        assert t_not(F) is T

    def test_unknown_stays_unknown(self):
        assert t_not(U) is U

    def test_double_not(self):
        assert t_not(t_not(T)) is T
        assert t_not(t_not(F)) is F
        assert t_not(t_not(U)) is U


class TestMixedNesting:
    def test_medical_area_or_beds(self):
        assert t_or(T, U) is T

    def test_medical_both_false(self):
        assert t_or(F, F) is F

    def test_exclusion_and_use(self):
        assert t_and(T, T) is T
        assert t_and(T, U) is U
        assert t_and(T, F) is F