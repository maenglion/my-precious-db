"""Ticket 013h: pg_trgm 기반 residual 클러스터링."""

from datetime import date

import pytest

from src.assessment.engine import run_assessment
from src.review.cluster import (
    find_similar_residuals,
    get_cluster_details,
    normalize_signature,
)


pytestmark = pytest.mark.integration

AS_OF = date(2026, 9, 15)


class TestNormalizeSignature:
    def test_basic(self):
        assert normalize_signature("scope:MEDICAL:RULE_COVERAGE") == \
               "scope_medical_rule_coverage"

    def test_unicode(self):
        assert normalize_signature("스코프:의료기관") == "스코프_의료기관"

    def test_empty(self):
        assert normalize_signature("") == ""

    def test_repeated_separators(self):
        assert normalize_signature("a:::b___c") == "a_b_c"


class TestFindSimilarResiduals:
    def test_no_residuals_no_clusters(self, db_conn, seeded):
        clusters = find_similar_residuals(db_conn)
        assert clusters == []

    def test_below_min_occurrence_no_cluster(self, db_conn, seeded):
        # 두 시설 각각 1회씩 RULE_COVERAGE → total 2 (< 3)
        fac_a = _make_facility(db_conn, "PARTIAL_TEST")
        fac_b = _make_facility(db_conn, "PARTIAL_TEST")
        run_assessment(db_conn, fac_a, AS_OF, persist=True)
        run_assessment(db_conn, fac_b, AS_OF, persist=True)

        clusters = find_similar_residuals(db_conn, min_occurrence=3)
        assert clusters == []

    def test_similar_signatures_cluster(self, db_conn, seeded):
        # 같은 scope (PARTIAL_TEST) 시설 2개
        # 같은 signature → 이미 UPSERT로 하나로 합쳐짐
        # 클러스터 테스트를 위해 서로 다른 scope_key를 만들되 유사하게
        fac_a = _make_facility(db_conn, "PARTIAL_TEST")
        for _ in range(2):
            run_assessment(db_conn, fac_a, AS_OF, persist=True)

        clusters = find_similar_residuals(db_conn, min_occurrence=2)
        # 시설 1개, signature 1개 → self-join에는 짝 없음
        # 시설별 클러스터는 감지 안 됨 (시설별 row 1개)
        # → total_occurrence 기반 판단 필요

        # 이건 다음 티켓: 시설별 count 누적과 시그니처 클러스터 분리
        # 지금은 클러스터가 안 잡히는 게 맞음
        assert clusters == []

    def test_cross_facility_similar_signatures_cluster(self, db_conn, seeded):
        # 시설 2개가 같은 signature (scope:PARTIAL_TEST:RULE_COVERAGE)
        fac_a = _make_facility(db_conn, "PARTIAL_TEST")
        fac_b = _make_facility(db_conn, "PARTIAL_TEST")
        run_assessment(db_conn, fac_a, AS_OF, persist=True)
        run_assessment(db_conn, fac_b, AS_OF, persist=True)

        # 두 residual signature 완전 동일 → similarity=1.0
        clusters = find_similar_residuals(
            db_conn, similarity_threshold=0.5, min_occurrence=2
        )
        assert len(clusters) >= 1
        c = clusters[0]
        assert c["total_occurrence"] >= 2
        assert len(c["members"]) == 2


class TestClusterDetails:
    def test_details_returned(self, db_conn, seeded):
        fac_a = _make_facility(db_conn, "PARTIAL_TEST")
        fac_b = _make_facility(db_conn, "PARTIAL_TEST")
        run_assessment(db_conn, fac_a, AS_OF, persist=True)
        run_assessment(db_conn, fac_b, AS_OF, persist=True)

        clusters = find_similar_residuals(
            db_conn, similarity_threshold=0.5, min_occurrence=2
        )
        assert len(clusters) >= 1
        details = get_cluster_details(db_conn, clusters[0]["members"])
        assert len(details) == len(clusters[0]["members"])
        for d in details:
            assert d["residual_type"] == "RULE_COVERAGE"


# helper

def _make_facility(conn, scope_key):
    import uuid
    import json
    fac_id = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO core.facility (facility_id, name) VALUES (%s, %s)",
            (fac_id, f"test-{scope_key}"),
        )
        cur.execute(
            "INSERT INTO core.facility_fact (facility_id, fact_key, value_json) "
            "VALUES (%s, 'facility_scope', %s::jsonb)",
            (fac_id, json.dumps(scope_key)),
        )
    conn.commit()
    return fac_id

class TestClusterOccurrenceMath:
    def test_two_members_each_once_total_is_two(self, db_conn, seeded):
        fac_a = _make_facility(db_conn, "PARTIAL_TEST")
        fac_b = _make_facility(db_conn, "PARTIAL_TEST")
        run_assessment(db_conn, fac_a, AS_OF, persist=True)
        run_assessment(db_conn, fac_b, AS_OF, persist=True)

        clusters = find_similar_residuals(
            db_conn, similarity_threshold=0.5, min_occurrence=2
        )
        assert len(clusters) == 1
        assert clusters[0]["total_occurrence"] == 2
        assert len(clusters[0]["members"]) == 2

    def test_member_occurrence_count_accumulated(self, db_conn, seeded):
        # fac_a 3회 (occurrence=3), fac_b 1회 (occurrence=1)
        fac_a = _make_facility(db_conn, "PARTIAL_TEST")
        fac_b = _make_facility(db_conn, "PARTIAL_TEST")
        for _ in range(3):
            run_assessment(db_conn, fac_a, AS_OF, persist=True)
        run_assessment(db_conn, fac_b, AS_OF, persist=True)

        clusters = find_similar_residuals(
            db_conn, similarity_threshold=0.5, min_occurrence=2
        )
        assert len(clusters) == 1
        # total = 3 + 1 = 4
        assert clusters[0]["total_occurrence"] == 4
        assert len(clusters[0]["members"]) == 2