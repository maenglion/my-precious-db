class OllamaError(Exception):
    """Ollama 연동 기본 예외."""

class OllamaUnavailable(OllamaError):
    """서버 미기동/네트워크 실패."""

class OllamaResponseError(OllamaError):
    """응답 파싱 실패 또는 비정상 응답."""