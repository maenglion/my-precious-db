import pytest
from src.integrations.ollama import OllamaClient, OllamaUnavailable

@pytest.mark.integration
def test_ollama_ping():
    """실제 로컬 Ollama 호출. CI에서는 skip."""
    client = OllamaClient()
    result = client.chat(
        system="Respond in JSON only.",
        user='Return {"ok": true}.',
    )
    assert isinstance(result, dict)
    assert result.get("ok") is True