"""Residual 클러스터링 (v0.2 §14.1 + §14.2).

pg_trgm similarity 기반. exact GROUP BY가 아니다.

파이프라인:
    signature 정규화 (normalize)
    ↓
    exact alias matching (지금은 생략)
    ↓
    pg_trgm similarity (threshold 이상)
    ↓
    클러스터 묶음
    ↓
    클러스터 내 반복 수 확인
"""

from __future__ import annotations

import os
import re

import psycopg

# 초기 운영 threshold — config로 분리 (v0.2 §14.2)
SIMILARITY_THRESHOLD = float(
    os.environ.get("RESIDUAL_SIMILARITY_THRESHOLD", "0.6")
)
CLUSTER_MIN_OCCURRENCE = int(
    os.environ.get("RESIDUAL_CLUSTER_MIN_OCCURRENCE", "3")
)


def normalize_signature(sig: str) -> str:
    """signature 정규화.

    - 소문자
    - 공백/특수문자 → 단일 _ 로
    - 앞뒤 _ 제거
    """
    if not sig:
        return ""
    s = sig.lower()
    s = re.sub(r"[^a-z0-9가-힣]+", "_", s)
    return s.strip("_")


def find_similar_residuals(
    conn: psycopg.Connection,
    *,
    similarity_threshold: float | None = None,
    min_occurrence: int | None = None,
) -> list[dict]:
    """유사 residual 클러스터 조회.

    Returns:
        [{"cluster_key": str, "members": [residual_id...],
          "total_occurrence": int, "sample_signature": str}]
    """
    thr = (
        similarity_threshold if similarity_threshold is not None
        else SIMILARITY_THRESHOLD
    )
    min_occ = (
        min_occurrence if min_occurrence is not None
        else CLUSTER_MIN_OCCURRENCE
    )

    with conn.cursor() as cur:
        # pg_trgm similarity 기반 self-join
        cur.execute(
            """
            SELECT
                a.residual_id AS a_id,
                b.residual_id AS b_id,
                a.signature   AS a_sig,
                b.signature   AS b_sig,
                a.occurrence_count AS a_occ,
                b.occurrence_count AS b_occ,
                similarity(a.signature, b.signature) AS sim
            FROM review.residual_item a
            JOIN review.residual_item b
              ON a.residual_id < b.residual_id
             AND a.residual_type = b.residual_type
             AND a.status = 'ACCUMULATING'
             AND b.status = 'ACCUMULATING'
            WHERE similarity(a.signature, b.signature) >= %s
            ORDER BY sim DESC
            """,
            (thr,),
        )
        pairs = cur.fetchall()

    clusters = _build_clusters(pairs, min_occ)
    return clusters


def _build_clusters(pairs: list[dict], min_occ: int) -> list[dict]:
    """union-find로 클러스터 묶음.

    total_occurrence는 클러스터 구성원 각각의 occurrence_count 합.
    """
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        while parent.get(x, x) != x:
            parent[x] = parent.get(parent[x], parent[x])
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for p in pairs:
        a, b = str(p["a_id"]), str(p["b_id"])
        parent.setdefault(a, a)
        parent.setdefault(b, b)
        union(a, b)

    # 그룹핑: 멤버별 occurrence_count를 dict로 보관 (중복 가산 방지)
    groups: dict[str, dict] = {}
    for p in pairs:
        a, b = str(p["a_id"]), str(p["b_id"])
        root = find(a)
        g = groups.setdefault(root, {
            "cluster_key": root,
            "member_occurrences": {},
            "sample_signature": p["a_sig"],
        })
        g["member_occurrences"][a] = p["a_occ"]
        g["member_occurrences"][b] = p["b_occ"]
        if p["a_sig"]:
            g["sample_signature"] = p["a_sig"]

    # 필터: total >= min_occ
    result = []
    for g in groups.values():
        total = sum(g["member_occurrences"].values())
        if total >= min_occ:
            result.append({
                "cluster_key": g["cluster_key"],
                "members": sorted(g["member_occurrences"].keys()),
                "total_occurrence": total,
                "sample_signature": g["sample_signature"],
            })
    return result


def get_cluster_details(
    conn: psycopg.Connection,
    residual_ids: list[str],
) -> list[dict]:
    """클러스터 구성원의 요약 정보."""
    if not residual_ids:
        return []
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT residual_id, residual_type, signature,
                   occurrence_count, details
            FROM review.residual_item
            WHERE residual_id = ANY(%s)
            ORDER BY occurrence_count DESC
            """,
            (residual_ids,),
        )
        return list(cur.fetchall())