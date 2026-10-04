"""Deterministic offline provider for TESTS and wiring checks only.

It "sees" images by reading the FILENAME (red-fox_01.jpg -> subject "red fox"), so it proves the
pipeline/guard logic, not vision quality. Never use it to produce EVIDENCE.md numbers.
Filename switches: blurry/unclear -> low confidence; flaky -> first 2 calls fail; garbage -> invalid JSON.
"""
import json
import math
import re
import zlib

import numpy as np

from ..errors import ProviderError
from ..taxonomy import load_taxonomy
from .base import Usage

HASH_DIMS = 128
STOP = {"the", "and", "for", "with", "that", "this", "are", "was", "from", "into", "its", "their", "his", "her", "has", "have", "can", "but", "not", "you", "your", "all", "any"}


class MockProvider:
    name = "mock"
    vision_model = "mock-vision"
    embed_model = "mock-embed"

    def __init__(self, s):
        self.tax = load_taxonomy(s.taxonomy_path)
        self._names = list(self.tax.subjects)
        self._cats = self.tax.categories
        self._calls: dict[str, int] = {}
        self._path_prompt = re.compile(r"FILENAME_HINT=(\S+)")

    def describe_image(self, data: bytes, mime: str, prompt: str) -> tuple[str, Usage]:
        m = self._path_prompt.search(prompt)
        stem = (m.group(1) if m else "unknown").rsplit(".", 1)[0]
        n = self._calls[stem] = self._calls.get(stem, 0) + 1
        if "flaky" in stem and n <= 2:
            raise ProviderError("mock transient failure")
        if "garbage" in stem:
            return "this is not json", Usage(100, 5)
        base = re.sub(r"_\d+$", "", stem).replace("-", " ")
        if "blurry" in stem or "unclear" in stem:
            subject, category, conf = "unidentified object", "other", 0.3
        else:
            subject, conf = base.replace(" flaky", ""), 0.93
            category = self.tax.category_of(self.tax.canonicalize(subject)) or "other"
        out = {"subject": subject, "category": category, "attributes": [category, "photo"],
               "caption": f"A photo of {subject} in a natural setting", "confidence": conf}
        return json.dumps(out), Usage(100, 40)

    def embed(self, text: str) -> tuple[list[float], Usage]:
        t = text.lower()
        ns, nc = len(self._names), len(self._cats)
        vec = np.zeros(ns + nc + HASH_DIMS)
        for i, name in enumerate(self._names):
            c = self.tax.count(name, t)
            if c:
                w = 1 + math.log(c)
                vec[i] += w
                vec[ns + self._cats.index(self.tax.subjects[name].category)] += 0.4 * w
        for tok in re.findall(r"[a-z]+", t):
            if len(tok) > 2 and tok not in STOP:
                vec[ns + nc + zlib.crc32(tok.encode()) % HASH_DIMS] += 0.1
        return vec.tolist(), Usage(max(1, len(text) // 4), 0)
