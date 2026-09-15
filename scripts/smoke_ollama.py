import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.integrations.ollama import OllamaClient  # noqa: E402

client = OllamaClient()
result = client.chat(
    system="Respond in JSON only.",
    user='Return {"ping": "pong"}.',
)
print(result)