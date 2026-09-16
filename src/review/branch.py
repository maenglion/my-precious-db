"""Residual type → branch 분류 (DL-012, DL-013).

LLM 없음. 결정적 매핑.

branch 3종:
    REPAIR   — 파서/수집/버전/식별 문제. 온톨로지 확장 아님.
    RULE     — rule/scope 커버리지 문제. LLM 호출 없음.
    ONTOLOGY — ontology 확장 후보. retrieval → LLM 경로.
"""

from __future__ import annotations


BRANCH_MAP: dict[str, str] = {
    # REPAIR — 데이터 수집/파서/버전/식별 이슈
    "PARSER": "REPAIR",
    "MISSING_FACT": "REPAIR",
    "SOURCE_CONFLICT": "REPAIR",
    "IDENTITY": "REPAIR",
    "LAW_VERSION_CONFLICT": "REPAIR",
    # RULE — rule/scope 커버리지
    "RULE_COVERAGE": "RULE",
    # ONTOLOGY — ontology 확장 후보
    "UNMAPPED_SOURCE_TYPE": "ONTOLOGY",
}


VALID_BRANCHES = frozenset({"REPAIR", "RULE", "ONTOLOGY"})


def classify_branch(residual_type: str) -> str | None:
    """residual_type → branch.

    Returns:
        "REPAIR" | "RULE" | "ONTOLOGY" | None (미분류)
    """
    if not residual_type:
        return None
    return BRANCH_MAP.get(residual_type)