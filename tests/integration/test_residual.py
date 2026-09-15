"""Phase 7: residual 실제 생성 검증."""

from datetime import date

import pytest

from src.assessment.engine import run_assessment
from src.assessment.verdict import Verdict


pytestmark = pytest.mark.integration

AS_OF = date(2026, 9, 15)


def _count_residuals(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) AS n FROM review.residual_item")
        return cur.fetchone()["n"]


def _fetch_residuals(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT residual_type, signature, details, status, occurrence_count "
            "FROM review.residual_item ORDER BY first_seen_at"
        )
        return cur.fetchall()


class TestResidualMissingScopeFact:
    def test_no_scope_fact_creates_missing_fact_residual(self, db_conn, seeded):
        # t01은 facility_scope fact가 있음 -> 제거하고 다시 seed
        # 별도 facility를 만들기보다 그냥 시설 하나 추가
        fac_id = _make_facility_without_scope(db_conn)

        out = run_assessment(db_conn, fac_id, AS_OF, persist=True)

        assert out.verdict is Verdict.INDETERMINATE
        assert out.residual_id is not None

        rows = _fetch_residuals(db_conn)
        matching = [r for r in rows if str(r["details"].get("reason")) == "MISSING_SCOPE_FACT"]
        assert len(matching) == 1
        r = matching[0]
        assert r["residual_type"] == "MISSING_FACT"
        assert r["occurrence_count"] == 1
        assert r["status"] == "ACCUMULATING"


class TestResidualPartialCoverage:
    def test_partial_coverage_creates_rule_coverage_residual(self, db_conn, seeded):
        # PARTIAL_TEST scope + 그 scope를 가진 facility 새로 추가
        fac_id = _make_facility(db_conn, scope_key="PARTIAL_TEST")

        out = run_assessment(db_conn, fac_id, AS_OF, persist=True)

        assert out.verdict is Verdict.INDETERMINATE
        assert out.residual_id is not None

        rows = _fetch_residuals(db_conn)
        matching = [r for r in rows if r["residual_type"] == "RULE_COVERAGE"]
        assert len(matching) == 1
        assert str(matching[0]["details"].get("reason")) == "RULE_COVERAGE"


class TestNoResidualOnResolvedScope:
    def test_resolved_scope_creates_no_residual(self, db_conn, seeded):
        # t01은 scope resolved -> residual 0
        fac_id = seeded["facilities"]["t01"]
        out = run_assessment(db_conn, fac_id, AS_OF, persist=True)

        assert out.verdict is Verdict.APPLICABLE
        assert out.residual_id is None
        assert _count_residuals(db_conn) == 0


# ---------- helpers ----------

def _make_facility(db_conn, *, scope_key, facts=None):
    import uuid
    import json

    fac_id = str(uuid.uuid4())
    facts = facts or {}
    with db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO core.facility (facility_id, name) VALUES (%s, %s)",
            (fac_id, f"test-{scope_key}"),
        )
        cur.execute(
            "INSERT INTO core.facility_fact (facility_id, fact_key, value_json) "
            "VALUES (%s, 'facility_scope', %s::jsonb)",
            (fac_id, json.dumps(scope_key)),
        )
        for k, v in facts.items():
            cur.execute(
                "INSERT INTO core.facility_fact (facility_id, fact_key, value_json) "
                "VALUES (%s, %s, %s::jsonb)",
                (fac_id, k, json.dumps(v)),
            )
    db_conn.commit()
    return fac_id


def _make_facility_without_scope(db_conn):
    import uuid

    fac_id = str(uuid.uuid4())
    with db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO core.facility (facility_id, name) VALUES (%s, %s)",
            (fac_id, "test-no-scope"),
        )
    db_conn.commit()
    return fac_id