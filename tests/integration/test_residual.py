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

class TestResidualAccumulation:
    def test_same_signature_increments_count(self, db_conn, seeded):
        fac_id = _make_facility_without_scope(db_conn)

        # 1회차
        out1 = run_assessment(db_conn, fac_id, AS_OF, persist=True)
        assert out1.residual_id is not None
        rows1 = _fetch_residuals(db_conn)
        assert len(rows1) == 1
        assert rows1[0]["occurrence_count"] == 1

        # 2회차 — 같은 시설, 같은 원인
        out2 = run_assessment(db_conn, fac_id, AS_OF, persist=True)
        assert out2.residual_id == out1.residual_id  # 같은 row 갱신
        rows2 = _fetch_residuals(db_conn)
        assert len(rows2) == 1  # 새 row 안 생김
        assert rows2[0]["occurrence_count"] == 2

        # 3회차
        run_assessment(db_conn, fac_id, AS_OF, persist=True)
        rows3 = _fetch_residuals(db_conn)
        assert len(rows3) == 1
        assert rows3[0]["occurrence_count"] == 3

    def test_different_facilities_same_signature_separate_rows(self, db_conn, seeded):
        fac_a = _make_facility_without_scope(db_conn)
        fac_b = _make_facility_without_scope(db_conn)

        run_assessment(db_conn, fac_a, AS_OF, persist=True)
        run_assessment(db_conn, fac_b, AS_OF, persist=True)

        rows = _fetch_residuals(db_conn)
        # 시설이 다르면 각자 row (시설별 카운트)
        assert len(rows) == 2
        assert all(r["occurrence_count"] == 1 for r in rows)

    def test_last_seen_at_updates_on_accumulate(self, db_conn, seeded):
        fac_id = _make_facility_without_scope(db_conn)

        run_assessment(db_conn, fac_id, AS_OF, persist=True)
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT first_seen_at, last_seen_at FROM review.residual_item"
            )
            first = cur.fetchone()
        assert first["first_seen_at"] == first["last_seen_at"]

        # 시간 간격 만들기
        import time
        time.sleep(1.1)

        run_assessment(db_conn, fac_id, AS_OF, persist=True)
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT first_seen_at, last_seen_at, occurrence_count "
                "FROM review.residual_item"
            )
            second = cur.fetchone()
        assert second["occurrence_count"] == 2
        assert second["first_seen_at"] == first["first_seen_at"]  # 안 바뀜
        assert second["last_seen_at"] > first["last_seen_at"]     # 갱신됨