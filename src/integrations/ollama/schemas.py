from dataclasses import dataclass, field


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class ChatOptions:
    temperature: float = 0.2


@dataclass
class ChatRequest:
    model: str
    messages: list[ChatMessage]
    stream: bool = False
    think: bool = False
    format: str = "json"
    options: ChatOptions = field(default_factory=ChatOptions)

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in self.messages],
            "stream": self.stream,
            "think": self.think,
            "format": self.format,
            "options": {"temperature": self.options.temperature},
        }