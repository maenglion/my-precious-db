"""T01~T09 시나리오 integration test — 실제 Railway PostgreSQL."""

from datetime import date

import pytest

from src.assessment.engine import run_assessment
from src.assessment.verdict import Verdict


pytestmark = pytest.mark.integration

AS_OF = date(2026, 9, 15)


def _run(conn, seeded, name):
    return run_assessment(conn, seeded["facilities"][name], AS_OF, persist=True)


class TestT01toT09:
    def test_t01_general_office_applicable(self, db_conn, seeded):
        out = _run(db_conn, seeded, "t01")
        assert out.verdict is Verdict.APPLICABLE
        assert out.matched_rule_id == seeded["rule_office_inc"]

    def test_t02_officetel_excluded(self, db_conn, seeded):
        out = _run(db_conn, seeded, "t02")
        assert out.verdict is Verdict.EXCLUDED
        assert out.matched_rule_id == seeded["rule_officetel_exc"]

    def test_t03_area_below_not_applicable(self, db_conn, seeded):
        out = _run(db_conn, seeded, "t03")
        assert out.verdict is Verdict.NOT_APPLICABLE

    def test_t04_medical_area_below_beds_ok(self, db_conn, seeded):
        out = _run(db_conn, seeded, "t04")
        assert out.verdict is Verdict.APPLICABLE
        assert out.matched_rule_id == seeded["rule_medical_inc"]

    def test_t05_medical_area_ok_beds_below(self, db_conn, seeded):
        out = _run(db_conn, seeded, "t05")
        assert out.verdict is Verdict.APPLICABLE

    def test_t06_medical_both_below(self, db_conn, seeded):
        out = _run(db_conn, seeded, "t06")
        assert out.verdict is Verdict.NOT_APPLICABLE

    def test_t07_medical_beds_unknown(self, db_conn, seeded):
        out = _run(db_conn, seeded, "t07")
        assert out.verdict is Verdict.INDETERMINATE

    def test_t08_large_store_applicable(self, db_conn, seeded):
        out = _run(db_conn, seeded, "t08")
        assert out.verdict is Verdict.APPLICABLE

    def test_t09_large_store_excluded(self, db_conn, seeded):
        out = _run(db_conn, seeded, "t09")
        assert out.verdict is Verdict.EXCLUDED
        assert out.matched_rule_id == seeded["rule_large_exc"]