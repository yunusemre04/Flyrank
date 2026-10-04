import base64

import httpx

from ..errors import ProviderError
from ..schemas import ImageTags
from .base import Usage


class OllamaProvider:
    name = "ollama"

    def __init__(self, s):
        self._host = s.ollama_host.rstrip("/")
        self.vision_model = s.ollama_vision_model
        self.embed_model = s.ollama_embed_model

    def _post(self, path: str, payload: dict) -> dict:
        try:
            r = httpx.post(f"{self._host}{path}", json=payload, timeout=300)
        except httpx.HTTPError as e:
            raise ProviderError(f"ollama unreachable: {type(e).__name__}") from e
        if r.status_code >= 500:
            raise ProviderError(f"ollama HTTP {r.status_code}")
        if r.status_code >= 400:
            raise ProviderError(f"ollama HTTP {r.status_code} (is the model pulled?)", retriable=False)
        return r.json()

    def describe_image(self, data: bytes, mime: str, prompt: str) -> tuple[str, Usage]:
        payload = {
            "model": self.vision_model,
            "stream": False,
            "format": ImageTags.model_json_schema(),
            "options": {"temperature": 0.1},
            "messages": [{"role": "user", "content": prompt, "images": [base64.b64encode(data).decode()]}],
        }
        out = self._post("/api/chat", payload)
        try:
            text = out["message"]["content"]
        except (KeyError, TypeError) as e:
            raise ProviderError("ollama returned no message") from e
        return text, Usage(out.get("prompt_eval_count", 0), out.get("eval_count", 0))

    def embed(self, text: str) -> tuple[list[float], Usage]:
        out = self._post("/api/embed", {"model": self.embed_model, "input": text})
        try:
            return out["embeddings"][0], Usage(out.get("prompt_eval_count", max(1, len(text) // 4)), 0)
        except (KeyError, IndexError, TypeError) as e:
            raise ProviderError("ollama returned no embedding") from e
