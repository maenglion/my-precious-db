"""4-state 최종 판정 테스트 (v0.2 10장 + 12.1 coverage)."""

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


# ---------- coverage uncertainty (v0.2 12.1 RULE_COVERAGE) ----------

class TestCoverageUncertainty:
    def test_no_rules_scope_unresolved(self):
        # rule seed 누락 / 매핑 실패 -> 절대 NOT_APPLICABLE 금지
        assert v([], scope=SCOPE_BAD) is Verdict.INDETERMINATE

    def test_include_true_but_scope_unresolved(self):
        # 긍정 신호가 있어도 스코프 불확실하면 확정하지 않는다
        assert v([r("inc1", "INCLUDE", T)], scope=SCOPE_BAD) is Verdict.INDETERMINATE

    def test_exclude_true_but_scope_unresolved(self):
        # 제외 신호도 스코프 불확실 시 사람 검토로
        assert v([r("exc1", "EXCLUDE", T)], scope=SCOPE_BAD) is Verdict.INDETERMINATE

    def test_all_false_scope_unresolved(self):
        rs = [r("inc1", "INCLUDE", F), r("exc1", "EXCLUDE", F)]
        assert v(rs, scope=SCOPE_BAD) is Verdict.INDETERMINATE

    def test_unknown_scope_unresolved(self):
        assert v([r("inc1", "INCLUDE", U)], scope=SCOPE_BAD) is Verdict.INDETERMINATE


# ---------- scope resolved: v0.2 10장 ----------

class TestExcludeDominates:
    def test_exclude_true_wins(self):
        rs = [r("inc1", "INCLUDE", T), r("exc1", "EXCLUDE", T)]
        assert v(rs) is Verdict.EXCLUDED

    def test_exclude_true_beats_include_unknown(self):
        rs = [r("inc1", "INCLUDE", U), r("exc1", "EXCLUDE", T)]
        assert v(rs) is Verdict.EXCLUDED


class TestInclude:
    def test_include_true_no_exclude(self):
        assert v([r("inc1", "INCLUDE", T)]) is Verdict.APPLICABLE

    def test_include_true_with_other_false(self):
        rs = [r("inc1", "INCLUDE", T), r("inc2", "INCLUDE", F)]
        assert v(rs) is Verdict.APPLICABLE


class TestIndeterminate:
    def test_no_include_true_but_unknown(self):
        rs = [r("inc1", "INCLUDE", F), r("inc2", "INCLUDE", U)]
        assert v(rs) is Verdict.INDETERMINATE

    def test_exclude_unknown_causes_indeterminate(self):
        rs = [r("inc1", "INCLUDE", F), r("exc1", "EXCLUDE", U)]
        assert v(rs) is Verdict.INDETERMINATE

    def test_medical_area_false_beds_unknown(self):
        # T07: 의료기관, 면적 미달 + 병상 수 미상
        assert v([r("medical", "INCLUDE", U)]) is Verdict.INDETERMINATE


class TestNotApplicable:
    def test_all_false_scope_resolved(self):
        rs = [r("inc1", "INCLUDE", F), r("exc1", "EXCLUDE", F)]
        assert v(rs) is Verdict.NOT_APPLICABLE

    def test_no_rules_scope_resolved(self):
        # 스코프 확정 + 매칭 0 -> 진짜 대상 아님
        assert v([], scope=SCOPE_OK) is Verdict.NOT_APPLICABLE


# ---------- regression: T01/T02/T07 시나리오 ----------

class TestRegressionScenarios:
    def test_t01_general_office_applicable(self):
        # T01: 일반 업무시설, 면적 기준 충족
        rs = [r("office_include", "INCLUDE", T)]
        assert v(rs) is Verdict.APPLICABLE

    def test_t02_officetel_excluded(self):
        # T02: 오피스텔, 면적 충족하나 EXCLUDE rule TRUE
        rs = [
            r("office_include", "INCLUDE", T),
            r("officetel_exclude", "EXCLUDE", T),
        ]
        assert v(rs) is Verdict.EXCLUDED

    def test_t07_medical_indeterminate(self):
        # T07: 의료기관, 면적 미달 + 병상 미상
        rs = [r("medical_include", "INCLUDE", U)]
        assert v(rs) is Verdict.INDETERMINATE

    def test_rule_coverage_missing_seed(self):
        # rule seed 자체가 없음 -> INDETERMINATE (residual=RULE_COVERAGE)
        assert v([], scope=SCOPE_BAD) is Verdict.INDETERMINATE