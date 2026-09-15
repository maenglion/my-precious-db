"""Ontology candidate generation via Ollama (v0.2 §24 Phase 9, DL-011).

이 모듈은 판정 엔진(assessment/*)에서 import되지 않는다.
Ollama가 죽어도 판정은 무영향이어야 한다 (v0.2 §15).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from src.integrations.ollama import OllamaClient, OllamaError


SYSTEM_PROMPT = """당신은 중대재해처벌법 대응 시스템의 보조 분석 도구입니다.

주어진 residual cluster는 판정 엔진이 분류하지 못한 반복 패턴입니다.
이 패턴이 어떤 ontology candidate(개념 후보)로 승격될 수 있는지 제안하세요.

규칙:
- 반드시 JSON만 출력 (설명문/마크다운 금지)
- 후보가 없다고 판단되면 빈 배열
- 확신이 없으면 confidence를 낮게
- label은 한국어, 간결하게 (20자 이내)
- 관련 법령이 명확할 때만 related_laws에 명시, 불확실하면 빈 배열
- rationale은 왜 이 후보를 제안하는지 한국어로 1~3문장

응답 스키마:
{
  "candidates": [
    {
      "label": "string",
      "rationale": "string",
      "confidence": 0.0,
      "related_laws": ["string"]
    }
  ]
}
"""

MAX_MEMBERS_IN_PROMPT = 20


@dataclass
class Candidate:
    label: str
    rationale: str
    confidence: float
    related_laws: list[str] = field(default_factory=list)
    source_cluster_key: str = ""


def build_user_prompt(cluster: dict, details: list[dict]) -> str:
    """cluster + member details → user prompt."""
    lines = [
        f"cluster_key: {cluster.get('cluster_key', '')}",
        f"total_occurrence: {cluster.get('total_occurrence', 0)}",
        f"sample_signature: {cluster.get('sample_signature', '')}",
        "",
        "members:",
    ]
    for d in details[:MAX_MEMBERS_IN_PROMPT]:
        detail_blob = json.dumps(
            d.get("details") or {}, ensure_ascii=False
        )[:200]
        lines.append(
            f"- id={d.get('residual_id')} "
            f"type={d.get('residual_type')} "
            f"sig={d.get('signature')} "
            f"occ={d.get('occurrence_count')} "
            f"details={detail_blob}"
        )
    lines.append("")
    lines.append("이 cluster에 대해 ontology candidate를 제안하세요.")
    return "\n".join(lines)


def _coerce_candidate(raw: dict, cluster_key: str) -> Candidate | None:
    label = (raw.get("label") or "").strip()
    if not label:
        return None
    try:
        conf = float(raw.get("confidence", 0.0))
    except (TypeError, ValueError):
        conf = 0.0
    conf = max(0.0, min(1.0, conf))
    rl = raw.get("related_laws") or []
    if not isinstance(rl, list):
        rl = []
    return Candidate(
        label=label,
        rationale=str(raw.get("rationale") or "").strip(),
        confidence=conf,
        related_laws=[str(x) for x in rl],
        source_cluster_key=cluster_key,
    )


def generate_candidates_for_cluster(
    client: OllamaClient,
    cluster: dict,
    details: list[dict],
) -> list[Candidate]:
    """cluster 1건에 대해 후보 0~N개 생성. 실패 시 빈 리스트.

    - DB 저장 안 함
    - 후보는 사람 검수 큐로 (Phase 10)
    """
    user = build_user_prompt(cluster, details)
    try:
        raw = client.chat(SYSTEM_PROMPT, user)
    except OllamaError:
        return []

    if not isinstance(raw, dict):
        return []
    raw_cands = raw.get("candidates") or []
    if not isinstance(raw_cands, list):
        return []

    cluster_key = str(cluster.get("cluster_key", ""))
    result: list[Candidate] = []
    for c in raw_cands:
        if not isinstance(c, dict):
            continue
        cand = _coerce_candidate(c, cluster_key)
        if cand is not None:
            result.append(cand)
    return result