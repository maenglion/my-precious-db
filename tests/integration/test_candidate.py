"""013k/013M: candidate generation tests (mocked Ollama)."""

from src.review.candidate import (
    Candidate,
    build_user_prompt,
    generate_candidates_for_cluster,
)


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls: list[tuple[str, str]] = []

    def chat(self, system: str, user: str, **kwargs):
        self.calls.append((system, user))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


CLUSTER = {
    "cluster_key": "abc",
    "total_occurrence": 5,
    "sample_signature": "unknown_equipment_tag",
    "members": ["r1", "r2"],
}

DETAILS = [
    {
        "residual_id": "r1",
        "residual_type": "UNMAPPED_SOURCE_TYPE",
        "signature": "unknown_equipment_tag",
        "occurrence_count": 3,
        "details": {"raw": "설비번호 미상"},
    },
    {
        "residual_id": "r2",
        "residual_type": "UNMAPPED_SOURCE_TYPE",
        "signature": "unknown_equipment_tag_v2",
        "occurrence_count": 2,
        "details": {},
    },
]


def test_build_user_prompt_contains_cluster_info():
    prompt = build_user_prompt(CLUSTER, DETAILS)
    assert "abc" in prompt
    assert "unknown_equipment_tag" in prompt
    assert "r1" in prompt
    assert "r2" in prompt


def test_generate_returns_candidates():
    fake = FakeClient({
        "candidates": [
            {
                "action": "CLASS",
                "label": "설비 식별 실패",
                "parent": "",
                "rationale": "설비번호가 반복적으로 미상",
                "decision_gain": "다른 rule set 적용 필요",
                "confidence": 0.8,
                "related_laws": ["산안법 제38조"],
            }
        ]
    })
    out = generate_candidates_for_cluster(fake, CLUSTER, DETAILS)
    assert len(out) == 1
    c = out[0]
    assert c.action == "CLASS"
    assert c.label == "설비 식별 실패"
    assert c.confidence == 0.8
    assert c.decision_gain == "다른 rule set 적용 필요"
    assert c.related_laws == ["산안법 제38조"]
    assert c.source_cluster_key == "abc"


def test_generate_empty_candidates():
    fake = FakeClient({"candidates": []})
    out = generate_candidates_for_cluster(fake, CLUSTER, DETAILS)
    assert out == []


def test_generate_ollama_error_returns_empty():
    from src.integrations.ollama import OllamaUnavailable
    fake = FakeClient(OllamaUnavailable("down"))
    out = generate_candidates_for_cluster(fake, CLUSTER, DETAILS)
    assert out == []


def test_generate_skips_invalid_entries():
    fake = FakeClient({
        "candidates": [
            {"action": "CLASS", "label": "", "confidence": 0.5},
            {"rationale": "no action"},
            {"action": "BOGUS", "label": "?"},
            "not a dict",
            {
                "action": "MAPPING",
                "label": "정상",
                "confidence": "bad",
            },
        ]
    })
    out = generate_candidates_for_cluster(fake, CLUSTER, DETAILS)
    assert len(out) == 1
    assert out[0].label == "정상"
    assert out[0].action == "MAPPING"
    assert out[0].confidence == 0.0


def test_generate_clamps_confidence():
    fake = FakeClient({
        "candidates": [
            {"action": "CLASS", "label": "a", "confidence": 5.0},
            {"action": "CLASS", "label": "b", "confidence": -1.0},
        ]
    })
    out = generate_candidates_for_cluster(fake, CLUSTER, DETAILS)
    assert out[0].confidence == 1.0
    assert out[1].confidence == 0.0


def test_no_ontology_change_is_skipped():
    """DL-012: NO_ONTOLOGY_CHANGE 는 후보 리스트에서 제외."""
    fake = FakeClient({
        "candidates": [
            {
                "action": "NO_ONTOLOGY_CHANGE",
                "label": "설비 태그 미등록",
                "rationale": "기존 의료기관 alias 추가로 해결",
                "decision_gain": "없음",
                "confidence": 0.9,
            },
        ]
    })
    out = generate_candidates_for_cluster(fake, CLUSTER, DETAILS)
    assert out == []