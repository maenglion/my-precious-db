"""013k: candidate generation tests (mocked Ollama)."""

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
        "residual_type": "SCOPE_UNMATCHED",
        "signature": "unknown_equipment_tag",
        "occurrence_count": 3,
        "details": {"raw": "설비번호 미상"},
    },
    {
        "residual_id": "r2",
        "residual_type": "SCOPE_UNMATCHED",
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
                "label": "설비 식별 실패",
                "rationale": "설비번호가 반복적으로 미상",
                "confidence": 0.8,
                "related_laws": ["산안법 제38조"],
            }
        ]
    })
    out = generate_candidates_for_cluster(fake, CLUSTER, DETAILS)
    assert len(out) == 1
    assert out[0].label == "설비 식별 실패"
    assert out[0].confidence == 0.8
    assert out[0].related_laws == ["산안법 제38조"]
    assert out[0].source_cluster_key == "abc"


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
            {"label": "", "confidence": 0.5},          # label 없음 → skip
            {"rationale": "no label"},                  # label 없음 → skip
            "not a dict",                               # dict 아님 → skip
            {"label": "정상", "confidence": "bad"},     # confidence 파싱 실패 → 0.0
        ]
    })
    out = generate_candidates_for_cluster(fake, CLUSTER, DETAILS)
    assert len(out) == 1
    assert out[0].label == "정상"
    assert out[0].confidence == 0.0


def test_generate_clamps_confidence():
    fake = FakeClient({
        "candidates": [
            {"label": "a", "confidence": 5.0},
            {"label": "b", "confidence": -1.0},
        ]
    })
    out = generate_candidates_for_cluster(fake, CLUSTER, DETAILS)
    assert out[0].confidence == 1.0
    assert out[1].confidence == 0.0