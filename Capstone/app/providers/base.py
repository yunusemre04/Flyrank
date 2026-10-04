from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0


class Provider(Protocol):
    name: str
    vision_model: str
    embed_model: str

    def describe_image(self, data: bytes, mime: str, prompt: str) -> tuple[str, Usage]:
        """Return the model's raw text (expected to be JSON) plus token usage."""

    def embed(self, text: str) -> tuple[list[float], Usage]: ...
