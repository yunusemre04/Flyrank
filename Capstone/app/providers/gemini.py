import base64

import httpx

from ..errors import ProviderError
from ..schemas import GEMINI_TAG_SCHEMA
from .base import Usage

BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider:
    name = "gemini"

    def __init__(self, s):
        if not s.gemini_api_key:
            raise ProviderError("GEMINI_API_KEY is not set (get a free key at aistudio.google.com)", retriable=False)
        self._key = s.gemini_api_key
        self.vision_model = s.gemini_vision_model
        self.embed_model = s.gemini_embed_model

    def _post(self, path: str, payload: dict) -> dict:
        try:  # key travels in a header so it never lands in URLs or logs
            r = httpx.post(f"{BASE}/{path}", headers={"x-goog-api-key": self._key}, json=payload, timeout=90)
        except httpx.HTTPError as e:
            raise ProviderError(f"network error: {type(e).__name__}") from e
        if r.status_code == 429 or r.status_code >= 500:
            raise ProviderError(f"gemini HTTP {r.status_code}")
        if r.status_code >= 400:
            raise ProviderError(f"gemini HTTP {r.status_code}", retriable=False)
        return r.json()

    def describe_image(self, data: bytes, mime: str, prompt: str) -> tuple[str, Usage]:
        payload = {
            "contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode()}}]}],
            "generationConfig": {"responseMimeType": "application/json", "responseSchema": GEMINI_TAG_SCHEMA, "temperature": 0.1},
        }
        out = self._post(f"models/{self.vision_model}:generateContent", payload)
        try:
            text = out["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as e:
            raise ProviderError("gemini returned no candidates (blocked or empty)") from e
        u = out.get("usageMetadata", {})
        return text, Usage(u.get("promptTokenCount", 0), u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0))

    def embed(self, text: str) -> tuple[list[float], Usage]:
        payload = {
            "model": f"models/{self.embed_model}",
            "content": {"parts": [{"text": text}]},
            "taskType": "SEMANTIC_SIMILARITY",
            "outputDimensionality": 768,
        }
        out = self._post(f"models/{self.embed_model}:embedContent", payload)
        try:
            values = out["embedding"]["values"]
        except (KeyError, TypeError) as e:
            raise ProviderError("gemini returned no embedding") from e
        return values, Usage(max(1, len(text) // 4), 0)  # the embed endpoint reports no usage; estimate ~4 chars/token
