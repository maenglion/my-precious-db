"""Ticket 013g: residual -> ontology candidate 승격 검증."""

from datetime import date

import pytest

from src.assessment.engine import run_assessment
from src.review.promotion import promote_residuals, PROMOTABLE_TYPES


pytestmark = pytest.mark.integration

AS_OF = date(2026, 9, 15)


def _fetch_candidates(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT candidate_type, proposed_value, status, rationale "
            "FROM review.ontology_candidate ORDER BY created_at"
        )
        return cur.fetchall()


def _fetch_residual_status(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT residual_id, status, occurrence_count "
            "FROM review.residual_item"
        )
        return cur.fetchall()


def _make_facility_without_scope(conn):
    import uuid
    fac_id = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO core.facility (facility_id, name) VALUES (%s, %s)",
            (fac_id, "test-no-scope"),
        )
    conn.commit()
    return fac_id


class TestPromotionBelowThreshold:
    def test_below_min_occurrence_not_promoted(self, db_conn, seeded):
        fac = _make_facility_without_scope(db_conn)
        # 2회만 실행 (min=3)
        run_assessment(db_conn, fac, AS_OF, persist=True)
        run_assessment(db_conn, fac, AS_OF, persist=True)

        promoted = promote_residuals(db_conn, min_occurrence=3)
        assert promoted == []
        assert _fetch_candidates(db_conn) == []


class TestPromotionAtThreshold:
    def test_at_min_occurrence_promoted(self, db_conn, seeded):
        fac = _make_facility_without_scope(db_conn)
        # 3회 실행 (MISSING_FACT) — 하지만 MISSING_FACT는 PROMOTABLE 아님
        for _ in range(3):
            run_assessment(db_conn, fac, AS_OF, persist=True)

        promoted = promote_residuals(db_conn, min_occurrence=3)
        # MISSING_FACT는 승격 대상 아님
        assert promoted == []

    def test_promotable_type_promoted(self, db_conn, seeded):
        # PARTIAL_TEST scope → RULE_COVERAGE (승격 가능)
        fac = _make_facility_with_partial_scope(db_conn)
        for _ in range(3):
            run_assessment(db_conn, fac, AS_OF, persist=True)

        promoted = promote_residuals(db_conn, min_occurrence=3)
        assert len(promoted) == 1

        candidates = _fetch_candidates(db_conn)
        assert len(candidates) == 1
        c = candidates[0]
        assert c["candidate_type"] == "SCOPE"
        assert c["status"] == "PENDING"
        assert "PARTIAL_TEST" in c["proposed_value"]


class TestPromotedStatusTransition:
    def test_residual_status_becomes_promoted(self, db_conn, seeded):
        fac = _make_facility_with_partial_scope(db_conn)
        for _ in range(3):
            run_assessment(db_conn, fac, AS_OF, persist=True)

        promote_residuals(db_conn, min_occurrence=3)

        rows = _fetch_residual_status(db_conn)
        assert len(rows) == 1
        assert rows[0]["status"] == "PROMOTED"


class TestNoDuplicatePromotion:
    def test_second_promotion_is_noop(self, db_conn, seeded):
        fac = _make_facility_with_partial_scope(db_conn)
        for _ in range(3):
            run_assessment(db_conn, fac, AS_OF, persist=True)

        first = promote_residuals(db_conn, min_occurrence=3)
        assert len(first) == 1

        second = promote_residuals(db_conn, min_occurrence=3)
        assert second == []

        assert len(_fetch_candidates(db_conn)) == 1


# helper

def _make_facility_with_partial_scope(conn):
    import uuid
    import json
    fac_id = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO core.facility (facility_id, name) VALUES (%s, %s)",
            (fac_id, "test-partial"),
        )
        cur.execute(
            "INSERT INTO core.facility_fact (facility_id, fact_key, value_json) "
            "VALUES (%s, 'facility_scope', %s::jsonb)",
            (fac_id, json.dumps("PARTIAL_TEST")),
        )
    conn.commit()
    return fac_id