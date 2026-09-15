"""4-state 최종 판정 테스트 (v0.2 10장 + DL-001 + DL-003)."""

from src.assessment.logic import TruthValue
from src.assessment.verdict import RuleResult, Verdict, final_verdict

T = TruthValue.TRUE
F = TruthValue.FALSE
U = TruthValue.UNKNOWN

SCOPE_OK = True
SCOPE_BAD = False


def r(rule_id, effect, result):
    return RuleResult(rule_id=rule_id, name=rule_id, effect=effect, result=result)


def v(rs, *, scope=SCOPE_OK):
    return final_verdict(rs, candidate_scope_resolved=scope)


class TestCoverageUncertainty:
    def test_no_rules_scope_unresolved(self):
        assert v([], scope=SCOPE_BAD) is Verdict.INDETERMINATE

    def test_include_true_but_scope_unresolved(self):
        assert v([r("inc1", "INCLUDE", T)], scope=SCOPE_BAD) is Verdict.INDETERMINATE

    def test_exclude_true_but_scope_unresolved(self):
        assert v([r("exc1", "EXCLUDE", T)], scope=SCOPE_BAD) is Verdict.INDETERMINATE

    def test_all_false_scope_unresolved(self):
        rs = [r("inc1", "INCLUDE", F), r("exc1", "EXCLUDE", F)]
        assert v(rs, scope=SCOPE_BAD) is Verdict.INDETERMINATE

    def test_unknown_scope_unresolved(self):
        assert v([r("inc1", "INCLUDE", U)], scope=SCOPE_BAD) is Verdict.INDETERMINATE


class TestIncludeTruePath:
    def test_include_true_no_exclude(self):
        assert v([r("inc1", "INCLUDE", T)]) is Verdict.APPLICABLE

    def test_include_true_exclude_false(self):
        rs = [r("inc1", "INCLUDE", T), r("exc1", "EXCLUDE", F)]
        assert v(rs) is Verdict.APPLICABLE

    def test_include_true_exclude_true(self):
        rs = [r("inc1", "INCLUDE", T), r("exc1", "EXCLUDE", T)]
        assert v(rs) is Verdict.EXCLUDED

    def test_include_true_exclude_unknown(self):
        rs = [r("inc1", "INCLUDE", T), r("exc1", "EXCLUDE", U)]
        assert v(rs) is Verdict.INDETERMINATE

    def test_include_true_with_other_false(self):
        rs = [r("inc1", "INCLUDE", T), r("inc2", "INCLUDE", F)]
        assert v(rs) is Verdict.APPLICABLE


class TestIncludeUnknownPath:
    def test_include_unknown_no_exclude(self):
        assert v([r("inc1", "INCLUDE", U)]) is Verdict.INDETERMINATE

    def test_include_unknown_exclude_true(self):
        rs = [r("inc1", "INCLUDE", U), r("exc1", "EXCLUDE", T)]
        assert v(rs) is Verdict.INDETERMINATE


class TestIncludeFalsePath:
    def test_include_false_only(self):
        assert v([r("inc1", "INCLUDE", F)]) is Verdict.NOT_APPLICABLE

    def test_include_false_exclude_true(self):
        rs = [r("inc1", "INCLUDE", F), r("exc1", "EXCLUDE", T)]
        assert v(rs) is Verdict.NOT_APPLICABLE

    def test_include_false_exclude_unknown(self):
        rs = [r("inc1", "INCLUDE", F), r("exc1", "EXCLUDE", U)]
        assert v(rs) is Verdict.NOT_APPLICABLE

    def test_all_false(self):
        rs = [r("inc1", "INCLUDE", F), r("exc1", "EXCLUDE", F)]
        assert v(rs) is Verdict.NOT_APPLICABLE

    def test_no_rules_scope_resolved(self):
        assert v([], scope=SCOPE_OK) is Verdict.NOT_APPLICABLE


class TestRegressionScenarios:
    def test_t01_general_office_applicable(self):
        rs = [r("office_include", "INCLUDE", T)]
        assert v(rs) is Verdict.APPLICABLE

    def test_t02_officetel_excluded(self):
        rs = [
            r("office_include", "INCLUDE", T),
            r("officetel_exclude", "EXCLUDE", T),
        ]
        assert v(rs) is Verdict.EXCLUDED

    def test_t03_area_below_exclude_unknown(self):
        rs = [
            r("office_include", "INCLUDE", F),
            r("officetel_exclude", "EXCLUDE", U),
        ]
        assert v(rs) is Verdict.NOT_APPLICABLE

    def test_t07_medical_indeterminate(self):
        rs = [r("medical_include", "INCLUDE", U)]
        assert v(rs) is Verdict.INDETERMINATE

    def test_rule_coverage_missing_seed(self):
        assert v([], scope=SCOPE_BAD) is Verdict.INDETERMINATE