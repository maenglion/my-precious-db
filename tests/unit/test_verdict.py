"""4-state 최종 판정 테스트 (v0.2 10장)."""

from src.assessment.logic import TruthValue
from src.assessment.verdict import RuleResult, Verdict, final_verdict

T = TruthValue.TRUE
F = TruthValue.FALSE
U = TruthValue.UNKNOWN


def r(rule_id, effect, result):
    return RuleResult(rule_id=rule_id, name=rule_id, effect=effect, result=result)


class TestExcludeDominates:
    def test_exclude_true_wins(self):
        rs = [
            r("inc1", "INCLUDE", T),
            r("exc1", "EXCLUDE", T),
        ]
        assert final_verdict(rs) is Verdict.EXCLUDED

    def test_exclude_true_beats_include_unknown(self):
        rs = [
            r("inc1", "INCLUDE", U),
            r("exc1", "EXCLUDE", T),
        ]
        assert final_verdict(rs) is Verdict.EXCLUDED


class TestInclude:
    def test_include_true_no_exclude(self):
        rs = [r("inc1", "INCLUDE", T)]
        assert final_verdict(rs) is Verdict.APPLICABLE

    def test_include_true_with_other_false(self):
        rs = [
            r("inc1", "INCLUDE", T),
            r("inc2", "INCLUDE", F),
        ]
        assert final_verdict(rs) is Verdict.APPLICABLE


class TestIndeterminate:
    def test_no_include_true_but_unknown(self):
        rs = [
            r("inc1", "INCLUDE", F),
            r("inc2", "INCLUDE", U),
        ]
        assert final_verdict(rs) is Verdict.INDETERMINATE

    def test_exclude_unknown_causes_indeterminate(self):
        rs = [
            r("inc1", "INCLUDE", F),
            r("exc1", "EXCLUDE", U),
        ]
        assert final_verdict(rs) is Verdict.INDETERMINATE

    def test_medical_area_false_beds_unknown(self):
        # T07 시나리오: 의료기관, 면적 미달 + 병상 수 미상
        rs = [r("medical", "INCLUDE", U)]
        assert final_verdict(rs) is Verdict.INDETERMINATE


class TestNotApplicable:
    def test_all_false(self):
        rs = [
            r("inc1", "INCLUDE", F),
            r("exc1", "EXCLUDE", F),
        ]
        assert final_verdict(rs) is Verdict.NOT_APPLICABLE

    def test_no_rules(self):
        assert final_verdict([]) is Verdict.NOT_APPLICABLE