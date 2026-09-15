"""Residual → ontology candidate 승격 (v0.2 §12.3 + §14.2).

승격 조건:
    1. residual_type IN ('UNMAPPED_SOURCE_TYPE', 'RULE_COVERAGE')
    2. occurrence_count >= CANDIDATE_MIN_OCCURRENCE (기본 3)
    3. status = 'ACCUMULATING'
    4. 아직 ontology_candidate에 등록되지 않음

AI는 여기서 개입하지 않는다. 이건 규칙 기반 승격이다.
LLM 후보 생성은 별도 티켓 (Ollama).
"""

from __future__ import annotations

import os

import psycopg
from psycopg.types.json import Jsonb

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
        # 승격 대상 residual 조회
        cur.execute(
            """
            SELECT r.residual_id, r.residual_type, r.signature,
                   r.occurrence_count, r.details
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

            # residual 상태 전환
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