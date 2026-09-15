"""Integration test fixtures — 실제 Railway PostgreSQL.

매 테스트 시작 시:
    - TRUNCATE 모든 schema
    - 최소 seed (법령 stub / scope / rule / facility)

종료 후 cleanup은 다음 테스트의 시작 TRUNCATE가 담당.
"""

import json
import uuid
from datetime import date

import pytest

from src.db import connect


AS_OF = date(2026, 9, 15)

_TRUNCATE_TABLES = [
    "assess.predicate_evaluation",
    "assess.rule_evaluation",
    "assess.assessment",
    "review.residual_item",
    "audit.event",
    "core.facility_fact",
    "core.facility",
    "rule.expression",
    "rule.rule",
    "rule.scope",
    "law.reference_edge",
    "law.node",
    "law.statute",
    "ingest.source_block",
    "ingest.source_document",
]


def _cleanup(conn):
    # 이전 테스트 실패로 트랜잭션이 abort 상태일 수 있음
    conn.rollback()
    with conn.cursor() as cur:
        cur.execute(
            "TRUNCATE "
            + ", ".join(_TRUNCATE_TABLES)
            + " RESTART IDENTITY CASCADE"
        )
    conn.commit()


@pytest.fixture(scope="session")
def db_conn():
    """session-wide psycopg 연결."""
    with connect() as conn:
        yield conn


@pytest.fixture
def seeded(db_conn):
    """매 테스트마다 clean + seed."""
    _cleanup(db_conn)
    ids = _seed_all(db_conn)
    return ids


# ------------------------------------------------------------------
# seed
# ------------------------------------------------------------------

def _seed_all(conn):
    ids: dict = {}

    # 1) law.statute + law.node
    ids["statute"] = str(uuid.uuid4())
    ids["node_office"] = str(uuid.uuid4())
    ids["node_medical"] = str(uuid.uuid4())
    ids["node_large"] = str(uuid.uuid4())

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO law.statute "
            "(statute_id, name, statute_type, effective_from) "
            "VALUES (%s, %s, %s, %s)",
            (ids["statute"], "중처법 시행령 (test)",
             "PRESIDENTIAL_DECREE", date(2022, 1, 27)),
        )
        cur.execute(
            "INSERT INTO law.node "
            "(node_id, statute_id, path, node_type, text, effective_from) VALUES "
            "(%s, %s, 'decree.s3'::ltree, 'article', '업무시설 test', %s), "
            "(%s, %s, 'decree.s5'::ltree, 'article', '의료기관 test', %s), "
            "(%s, %s, 'decree.s7'::ltree, 'article', '대규모점포 test', %s)",
            (
                ids["node_office"], ids["statute"], date(2022, 1, 27),
                ids["node_medical"], ids["statute"], date(2022, 1, 27),
                ids["node_large"], ids["statute"], date(2022, 1, 27),
            ),
        )

    # 2) rule.scope
    ids["scope_office"] = str(uuid.uuid4())
    ids["scope_medical"] = str(uuid.uuid4())
    ids["scope_large"] = str(uuid.uuid4())
    ids["scope_partial"] = str(uuid.uuid4())

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO rule.scope "
            "(scope_id, scope_key, name, source_node_id, "
            " coverage_status, effective_from, status) VALUES "
            "(%s, 'OFFICE', '업무시설 test', %s, 'COMPLETE', %s, 'ACTIVE'), "
            "(%s, 'MEDICAL', '의료기관 test', %s, 'COMPLETE', %s, 'ACTIVE'), "
            "(%s, 'LARGE_STORE', '대규모점포 test', %s, 'COMPLETE', %s, 'ACTIVE'), "
            "(%s, 'PARTIAL_TEST', '부분검증 test', %s, 'PARTIAL', %s, 'ACTIVE')",
            (
                ids["scope_office"], ids["node_office"], date(2022, 1, 27),
                ids["scope_medical"], ids["node_medical"], date(2022, 1, 27),
                ids["scope_large"], ids["node_large"], date(2022, 1, 27),
                ids["scope_partial"], ids["node_office"], date(2022, 1, 27),
            ),
        )

    # 3) rule.rule
    ids["rule_office_inc"] = str(uuid.uuid4())
    ids["rule_officetel_exc"] = str(uuid.uuid4())
    ids["rule_medical_inc"] = str(uuid.uuid4())
    ids["rule_large_inc"] = str(uuid.uuid4())
    ids["rule_large_exc"] = str(uuid.uuid4())

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO rule.rule "
            "(rule_id, source_node_id, name, effect, priority, "
            " effective_from, status, scope_id) VALUES "
            "(%s, %s, 'office_include', 'INCLUDE', 100, %s, 'ACTIVE', %s), "
            "(%s, %s, 'officetel_exclude', 'EXCLUDE', 10, %s, 'ACTIVE', %s), "
            "(%s, %s, 'medical_include', 'INCLUDE', 100, %s, 'ACTIVE', %s), "
            "(%s, %s, 'large_store_include', 'INCLUDE', 100, %s, 'ACTIVE', %s), "
            "(%s, %s, 'large_store_exclude', 'EXCLUDE', 10, %s, 'ACTIVE', %s)",
            (
                ids["rule_office_inc"], ids["node_office"],
                date(2022, 1, 27), ids["scope_office"],
                ids["rule_officetel_exc"], ids["node_office"],
                date(2022, 1, 27), ids["scope_office"],
                ids["rule_medical_inc"], ids["node_medical"],
                date(2022, 1, 27), ids["scope_medical"],
                ids["rule_large_inc"], ids["node_large"],
                date(2022, 1, 27), ids["scope_large"],
                ids["rule_large_exc"], ids["node_large"],
                date(2022, 1, 27), ids["scope_large"],
            ),
        )

    # 4) rule.expression
    with conn.cursor() as cur:
        # office_include: area >= 3000
        cur.execute(
            "INSERT INTO rule.expression "
            "(expr_id, rule_id, parent_expr_id, expr_type, "
            " fact_key, operator, compare_value, sort_order) "
            "VALUES (%s, %s, NULL, 'PREDICATE', 'area', '>=', '3000'::jsonb, 0)",
            (str(uuid.uuid4()), ids["rule_office_inc"]),
        )

        # officetel_exclude: AND(use_type=OFFICE, subtype=OFFICETEL)
        and1 = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO rule.expression "
            "(expr_id, rule_id, parent_expr_id, expr_type, sort_order) "
            "VALUES (%s, %s, NULL, 'AND', 0)",
            (and1, ids["rule_officetel_exc"]),
        )
        cur.execute(
            "INSERT INTO rule.expression "
            "(expr_id, rule_id, parent_expr_id, expr_type, "
            " fact_key, operator, compare_value, sort_order) VALUES "
            "(%s, %s, %s, 'PREDICATE', 'use_type', '=', '\"OFFICE\"'::jsonb, 0), "
            "(%s, %s, %s, 'PREDICATE', 'subtype', '=', '\"OFFICETEL\"'::jsonb, 1)",
            (
                str(uuid.uuid4()), ids["rule_officetel_exc"], and1,
                str(uuid.uuid4()), ids["rule_officetel_exc"], and1,
            ),
        )

        # medical_include: OR(area >= 2000, beds >= 100)
        or1 = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO rule.expression "
            "(expr_id, rule_id, parent_expr_id, expr_type, sort_order) "
            "VALUES (%s, %s, NULL, 'OR', 0)",
            (or1, ids["rule_medical_inc"]),
        )
        cur.execute(
            "INSERT INTO rule.expression "
            "(expr_id, rule_id, parent_expr_id, expr_type, "
            " fact_key, operator, compare_value, sort_order) VALUES "
            "(%s, %s, %s, 'PREDICATE', 'area', '>=', '2000'::jsonb, 0), "
            "(%s, %s, %s, 'PREDICATE', 'beds', '>=', '100'::jsonb, 1)",
            (
                str(uuid.uuid4()), ids["rule_medical_inc"], or1,
                str(uuid.uuid4()), ids["rule_medical_inc"], or1,
            ),
        )

        # large_store_include: area >= 3000
        cur.execute(
            "INSERT INTO rule.expression "
            "(expr_id, rule_id, parent_expr_id, expr_type, "
            " fact_key, operator, compare_value, sort_order) "
            "VALUES (%s, %s, NULL, 'PREDICATE', 'area', '>=', '3000'::jsonb, 0)",
            (str(uuid.uuid4()), ids["rule_large_inc"]),
        )

        # large_store_exclude: AND(use_type=LARGE_STORE, subtype=EXCLUDED_TYPE)
        and2 = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO rule.expression "
            "(expr_id, rule_id, parent_expr_id, expr_type, sort_order) "
            "VALUES (%s, %s, NULL, 'AND', 0)",
            (and2, ids["rule_large_exc"]),
        )
        cur.execute(
            "INSERT INTO rule.expression "
            "(expr_id, rule_id, parent_expr_id, expr_type, "
            " fact_key, operator, compare_value, sort_order) VALUES "
            "(%s, %s, %s, 'PREDICATE', 'use_type', '=', '\"LARGE_STORE\"'::jsonb, 0), "
            "(%s, %s, %s, 'PREDICATE', 'subtype', '=', '\"EXCLUDED_TYPE\"'::jsonb, 1)",
            (
                str(uuid.uuid4()), ids["rule_large_exc"], and2,
                str(uuid.uuid4()), ids["rule_large_exc"], and2,
            ),
        )

    conn.commit()

    # 5) facilities + facts
    ids["facilities"] = _seed_facilities(conn)
    return ids


def _seed_facilities(conn):
    facilities: dict = {}

    def add(name: str, scope_key: str, facts: dict) -> None:
        fac_id = str(uuid.uuid4())
        facilities[name] = fac_id
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO core.facility (facility_id, name) VALUES (%s, %s)",
                (fac_id, name),
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

      # T01~T09
    add("t01", "OFFICE", {"area": 3500, "use_type": "OFFICE", "subtype": "GENERAL"})
    add("t02", "OFFICE", {"area": 3500, "use_type": "OFFICE", "subtype": "OFFICETEL"})
    add("t03", "OFFICE", {"area": 2000, "use_type": "OFFICE", "subtype": "GENERAL"})
    add("t04", "MEDICAL", {"area": 1000, "beds": 150})
    add("t05", "MEDICAL", {"area": 3000, "beds": 50})
    add("t06", "MEDICAL", {"area": 1000, "beds": 50})
    add("t07", "MEDICAL", {"area": 1000})
    add("t08", "LARGE_STORE", {"area": 5000, "use_type": "LARGE_STORE", "subtype": "NORMAL"})
    add("t09", "LARGE_STORE", {"area": 5000, "use_type": "LARGE_STORE", "subtype": "EXCLUDED_TYPE"})

    conn.commit()
    return facilities