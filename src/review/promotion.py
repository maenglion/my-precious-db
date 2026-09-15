"""Residual → ontology candidate 승격 (v0.2 §12.3 + §14.2 + DL-010).

승격 조건:
    1. residual_type IN ('UNMAPPED_SOURCE_TYPE', 'RULE_COVERAGE')
    2. occurrence_count >= CANDIDATE_MIN_OCCURRENCE (기본 3)
    3. status = 'ACCUMULATING'
    4. 아직 ontology_candidate에 등록되지 않음
    5. DL-010: RULE_COVERAGE는 source/parser/version 문제가 아닐 때만

AI는 여기서 개입하지 않는다. 규칙 기반 승격이다.
LLM 후보 생성은 별도 티켓 (Ollama).
"""

from __future__ import annotations

import os

import psycopg

CANDIDATE_MIN_OCCURRENCE = int(
    os.environ.get("CANDIDATE_MIN_OCCURRENCE", "3")
)

# ontology 후보로 승격 가능한 residual_type (v0.2 §12.3)
PROMOTABLE_TYPES = frozenset({"UNMAPPED_SOURCE_TYPE", "RULE_COVERAGE"})

# residual_type → candidate_type 매핑
_CANDIDATE_TYPE_MAP = {
    "UNMAPPED_SOURCE_TYPE": "CLASS",
    "RULE_COVERAGE": "SCOPE",
}

# DL-010: RULE_COVERAGE 승격 시 함께 확인해야 할 conflict 타입
_RULE_COVERAGE_CONFLICTS = (
    "PARSER",
    "LAW_VERSION_CONFLICT",
    "SOURCE_CONFLICT",
)


def promote_residuals(
    conn: psycopg.Connection,
    *,
    min_occurrence: int | None = None,
) -> list[str]:
    """승격 조건을 만족하는 residual을 ontology_candidate로 옮긴다.

    Returns:
        새로 생성된 candidate_id 리스트
    """
    min_occ = (
        min_occurrence if min_occurrence is not None
        else CANDIDATE_MIN_OCCURRENCE
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT r.residual_id, r.facility_id, r.residual_type,
                   r.signature, r.occurrence_count, r.details
            FROM review.residual_item r
            WHERE r.residual_type = ANY(%s)
              AND r.occurrence_count >= %s
              AND r.status = 'ACCUMULATING'
              AND NOT EXISTS (
                  SELECT 1 FROM review.ontology_candidate c
                  WHERE c.residual_id = r.residual_id
              )
            ORDER BY r.occurrence_count DESC, r.last_seen_at
            """,
            (list(PROMOTABLE_TYPES), min_occ),
        )
        rows = cur.fetchall()

        new_candidate_ids: list[str] = []
        for r in rows:
            candidate_type = _CANDIDATE_TYPE_MAP.get(r["residual_type"])
            if candidate_type is None:
                continue

            # DL-010: RULE_COVERAGE는 source/parser/version 문제 시 승격하지 않음
            if r["residual_type"] == "RULE_COVERAGE":
                facility_id = (
                    str(r["facility_id"]) if r.get("facility_id") else None
                )
                if _has_conflicting_residual(
                    conn,
                    facility_id,
                    conflict_types=_RULE_COVERAGE_CONFLICTS,
                ):
                    continue

            proposed_value = _proposed_value(r)
            parent_value = _parent_value(r)
            rationale = _rationale(r)

            cur.execute(
                """
                INSERT INTO review.ontology_candidate
                    (residual_id, candidate_type, proposed_value,
                     parent_value, rationale, status)
                VALUES (%s, %s, %s, %s, %s, 'PENDING')
                RETURNING candidate_id
                """,
                (r["residual_id"], candidate_type, proposed_value,
                 parent_value, rationale),
            )
            new_candidate_ids.append(str(cur.fetchone()["candidate_id"]))

            cur.execute(
                """
                UPDATE review.residual_item
                SET status = 'PROMOTED'
                WHERE residual_id = %s
                """,
                (r["residual_id"],),
            )

    conn.commit()
    return new_candidate_ids


def _has_conflicting_residual(
    conn: psycopg.Connection,
    facility_id: str | None,
    *,
    conflict_types: tuple[str, ...],
) -> bool:
    """같은 facility에 대해 특정 residual_type이 ACCUMULATING 상태로 있나.

    DL-010: RULE_COVERAGE 승격 gate.
    source/parser/version 문제가 있으면 RULE_COVERAGE는 ontology 부족이 아니다.
    """
    if facility_id is None:
        return False
    if not conflict_types:
        return False
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM review.residual_item
            WHERE facility_id = %s
              AND residual_type = ANY(%s)
              AND status = 'ACCUMULATING'
            LIMIT 1
            """,
            (facility_id, list(conflict_types)),
        )
        return cur.fetchone() is not None


def _proposed_value(row: dict) -> str:
    """signature에서 사람이 읽을 수 있는 제안값 추출."""
    sig = row["signature"] or ""
    details = row["details"] or {}
    if row["residual_type"] == "RULE_COVERAGE":
        scope_key = details.get("scope_key") or "UNKNOWN"
        return f"scope:{scope_key}"
    return sig


def _parent_value(row: dict) -> str | None:
    details = row["details"] or {}
    return details.get("scope_key")


def _rationale(row: dict) -> str:
    return (
        f"residual_type={row['residual_type']}, "
        f"occurrence_count={row['occurrence_count']}, "
        f"signature={row['signature']}"
    )