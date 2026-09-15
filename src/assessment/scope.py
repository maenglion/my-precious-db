"""Candidate Scope Registry + Coverage Resolution (Ticket 013a).

rule이 "없다"와 "scope 전체를 확인했고 실제로 없다"를 구분한다.

canonical scope fact_key = "facility_scope"
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import psycopg


CANONICAL_SCOPE_FACT_KEY = "facility_scope"

REASON_MISSING_SCOPE_FACT = "MISSING_SCOPE_FACT"
REASON_UNMAPPED_SCOPE = "UNMAPPED_SCOPE"
REASON_RULE_COVERAGE = "RULE_COVERAGE"
REASON_SOURCE_CONFLICT = "SOURCE_CONFLICT"
REASON_LAW_VERSION_CONFLICT = "LAW_VERSION_CONFLICT"

_RESIDUAL_MAP = {
    REASON_MISSING_SCOPE_FACT: "MISSING_FACT",
    REASON_UNMAPPED_SCOPE: "UNMAPPED_SOURCE_TYPE",
    REASON_RULE_COVERAGE: "RULE_COVERAGE",
    REASON_SOURCE_CONFLICT: "SOURCE_CONFLICT",
    REASON_LAW_VERSION_CONFLICT: "LAW_VERSION_CONFLICT",
}


@dataclass(frozen=True)
class ScopeResolution:
    resolved: bool
    scope_id: str | None
    scope_key: str | None
    reason: str | None


# ---------- 순수 판정 ----------

def resolve_scope_from_rows(
    *,
    scope_key: str | None,
    scope_rows: list[dict],
    as_of: date,
) -> ScopeResolution:
    """DB 없이 평가 가능한 순수 함수.

    A. scope_key None -> MISSING_SCOPE_FACT
    B. 매칭 scope 없음 -> UNMAPPED_SCOPE
    C. coverage_status != COMPLETE -> RULE_COVERAGE
    D. ACTIVE + as_of 유효 + COMPLETE -> resolved=True
    effective_from <= as_of < effective_to (또는 effective_to NULL)
    """
    if scope_key is None:
        return ScopeResolution(False, None, None, REASON_MISSING_SCOPE_FACT)

    matching = [r for r in scope_rows if r.get("scope_key") == scope_key]

    active_in_window = [
        r for r in matching
        if r.get("status") == "ACTIVE" and _effective_at(r, as_of)
    ]

    if not active_in_window:
        if matching:
            # 알려진 scope_key지만 지금 시점에 유효하지 않음
            return ScopeResolution(False, None, scope_key, REASON_LAW_VERSION_CONFLICT)
        return ScopeResolution(False, None, scope_key, REASON_UNMAPPED_SCOPE)

    # UNIQUE(scope_key, effective_from) 이므로 여러 개면 서로 다른 시점판
    active_in_window.sort(key=lambda r: r["effective_from"], reverse=True)
    chosen = active_in_window[0]

    if chosen.get("coverage_status") != "COMPLETE":
        return ScopeResolution(
            False, str(chosen["scope_id"]), scope_key, REASON_RULE_COVERAGE
        )

    return ScopeResolution(True, str(chosen["scope_id"]), scope_key, None)


def _effective_at(row: dict, as_of: date) -> bool:
    ef = row.get("effective_from")
    et = row.get("effective_to")
    if ef is None or ef > as_of:
        return False
    if et is not None and as_of >= et:
        return False
    return True


# ---------- residual 매핑 ----------

def scope_failure_to_residual_type(reason: str | None) -> str | None:
    """resolved=True(reason=None)면 None 반환."""
    if reason is None:
        return None
    return _RESIDUAL_MAP.get(reason)


# ---------- DB 로더 ----------

def load_scope_resolution(
    conn: psycopg.Connection,
    facility_id: str,
    as_of: date,
) -> ScopeResolution:
    """core.facility_fact -> rule.scope -> ScopeResolution.

    SQL 결과가 없다고 자동 COMPLETE 처리하지 않는다.
    """
    fact_sql = """
        SELECT fact_id, value_json, effective_from, effective_to
        FROM core.facility_fact
        WHERE facility_id = %s
          AND fact_key = %s
          AND (effective_from IS NULL OR effective_from <= %s)
          AND (effective_to IS NULL OR effective_to > %s)
        ORDER BY created_at DESC
    """
    with conn.cursor() as cur:
        cur.execute(
            fact_sql,
            (facility_id, CANONICAL_SCOPE_FACT_KEY, as_of, as_of),
        )
        fact_rows = cur.fetchall()

    if not fact_rows:
        return ScopeResolution(False, None, None, REASON_MISSING_SCOPE_FACT)

    scope_key = _extract_scope_key(fact_rows)
    if scope_key is None:
        return ScopeResolution(False, None, None, REASON_SOURCE_CONFLICT)

    scope_sql = """
        SELECT scope_id, scope_key, coverage_status, status,
               effective_from, effective_to
        FROM rule.scope
        WHERE scope_key = %s
    """
    with conn.cursor() as cur:
        cur.execute(scope_sql, (scope_key,))
        scope_rows = cur.fetchall()

    return resolve_scope_from_rows(
        scope_key=scope_key,
        scope_rows=list(scope_rows),
        as_of=as_of,
    )


def _extract_scope_key(fact_rows: list[dict]) -> str | None:
    """동일 시점 유효 fact 중 값이 갈리면 None(SOURCE_CONFLICT)."""
    values: set = set()
    for r in fact_rows:
        v = r.get("value_json")
        if isinstance(v, dict) and "value" in v:
            v = v["value"]
        values.add(v)
    if len(values) > 1:
        return None
    v = values.pop()
    if v is None:
        return None
    return str(v)


def load_rules_for_scope(
    conn: psycopg.Connection,
    scope_id: str,
    as_of: date,
) -> list[dict]:
    """향후 engine이 candidate rules 로딩 시 사용. 이 티켓에서는 연결 안 함."""
    sql = """
        SELECT rule_id, name, effect, priority, source_node_id
        FROM rule.rule
        WHERE scope_id = %s
          AND status = 'ACTIVE'
          AND effective_from <= %s
          AND (effective_to IS NULL OR effective_to > %s)
        ORDER BY priority, name
    """
    with conn.cursor() as cur:
        cur.execute(sql, (scope_id, as_of, as_of))
        return list(cur.fetchall())