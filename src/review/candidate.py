"""Ontology candidate generation via Ollama (v0.2 §24 Phase 9, DL-011, DL-012).

이 모듈은 판정 엔진(assessment/*)에서 import되지 않는다.
Ollama가 죽어도 판정은 무영향이어야 한다 (v0.2 §15).

DL-012: LLM은 action(ALIAS/MAPPING/CLASS/SCOPE/NO_ONTOLOGY_CHANGE)을
제안할 뿐 확정하지 않는다. 사람 검수 큐로 간다.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from src.integrations.ollama import OllamaClient, OllamaError


logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """당신은 중대재해처벌법 대응 시스템의 보조 분석 도구입니다.

주어진 residual cluster는 판정 엔진이 분류하지 못한 반복 패턴입니다.
이 패턴을 해결하기 위해 가장 **싼** 구조 변경을 제안하세요.

원칙 (DL-012):
- 증상으로 칸을 만들지 않는다.
- 가장 싼 구조 변경부터: ALIAS < MAPPING < CLASS < SCOPE
- 판정이 안 바뀌면 노드가 아니다.
- 새로 만들 필요가 없으면 NO_ONTOLOGY_CHANGE.

action 종류:
- ALIAS: 기존 클래스의 별칭 추가 (예: "OO메디컬센터" → 의료기관)
- MAPPING: 기존 유형에 매핑 (예: 두 유형 중 하나로 귀속)
- CLASS: 기존 어느 유형과도 다른 법적 성격 → 새 클래스
- SCOPE: 기존 판정 축 자체로 설명 안 됨 → 새 scope
- NO_ONTOLOGY_CHANGE: alias/mapping/rule repair 로 해결됨. 새 구조 불필요.

규칙:
- 반드시 JSON만 출력 (설명문/마크다운 금지)
- 후보가 없다고 판단되면 candidates: []
- 확신이 없으면 confidence를 낮게
- label은 한국어, 간결하게 (20자 이내)
- related_laws는 명확할 때만, 불확실하면 빈 배열
- decision_gain: 이 변경이 판정을 어떻게 바꾸는지 1문장. 바꾸지 않으면 "없음".

응답 스키마:
{
  "candidates": [
    {
      "action": "ALIAS | MAPPING | CLASS | SCOPE | NO_ONTOLOGY_CHANGE",
      "label": "string",
      "parent": "string",
      "rationale": "string",
      "decision_gain": "string",
      "confidence": 0.0,
      "related_laws": ["string"]
    }
  ]
}
"""

MAX_MEMBERS_IN_PROMPT = 20

VALID_ACTIONS = frozenset({
    "ALIAS",
    "MAPPING",
    "CLASS",
    "SCOPE",
    "NO_ONTOLOGY_CHANGE",
})


@dataclass
class Candidate:
    action: str
    label: str
    rationale: str
    confidence: float
    parent: str = ""
    decision_gain: str = ""
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
    lines.append(
        "이 cluster에 대해 가장 싼 구조 변경을 제안하세요. "
        "필요 없으면 NO_ONTOLOGY_CHANGE."
    )
    return "\n".join(lines)


def _coerce_candidate(raw: dict, cluster_key: str) -> Candidate | None:
    action = (raw.get("action") or "").strip().upper()
    if action not in VALID_ACTIONS:
        return None
    if action == "NO_ONTOLOGY_CHANGE":
        return None  # 후보 리스트에 남기지 않음
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
        action=action,
        label=label,
        rationale=str(raw.get("rationale") or "").strip(),
        confidence=conf,
        parent=str(raw.get("parent") or "").strip(),
        decision_gain=str(raw.get("decision_gain") or "").strip(),
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
    - NO_ONTOLOGY_CHANGE 는 로그만 남기고 리스트에서 제외
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
        elif (c.get("action") or "").strip().upper() == "NO_ONTOLOGY_CHANGE":
            logger.info(
                "cluster %s: NO_ONTOLOGY_CHANGE — %s",
                cluster_key,
                (c.get("rationale") or "")[:120],
            )
    return result