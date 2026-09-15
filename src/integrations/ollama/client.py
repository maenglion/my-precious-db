import json
from typing import Any

import httpx

from .exceptions import OllamaResponseError, OllamaUnavailable
from .schemas import ChatMessage, ChatOptions, ChatRequest

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3:8b"
DEFAULT_TIMEOUT = 60.0


class OllamaClient:
    """얇은 HTTP 클라이언트. 판정 엔진은 이 모듈을 import하지 않는다 (v0.2 §15)."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def chat(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        req = ChatRequest(
            model=self.model,
            messages=[
                ChatMessage(role="system", content=system),
                ChatMessage(role="user", content=user),
            ],
            options=ChatOptions(temperature=temperature),
        )
        try:
            resp = httpx.post(
                f"{self.base_url}/api/chat",
                json=req.to_dict(),
                timeout=self.timeout,
            )
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise OllamaUnavailable(str(e)) from e

        if resp.status_code != 200:
            raise OllamaResponseError(f"HTTP {resp.status_code}: {resp.text[:200]}")

        body = resp.json()
        content = body.get("message", {}).get("content", "")
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise OllamaResponseError(f"JSON parse failed: {content[:200]}") from e