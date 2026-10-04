"""Small subject taxonomy: lets the guard turn free text ("Vulpes vulpes", "foxes") into a canonical subject."""
import json
import re
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Subject:
    name: str
    category: str
    aliases: tuple[str, ...]


class Taxonomy:
    def __init__(self, subjects: list[Subject]):
        self.subjects = {s.name: s for s in subjects}
        self.categories = sorted({s.category for s in subjects})
        self._patterns: dict[str, list[tuple[str, re.Pattern]]] = {}
        for s in subjects:
            aliases = sorted({s.name.lower(), *[a.lower() for a in s.aliases]}, key=len, reverse=True)
            self._patterns[s.name] = [(a, re.compile(rf"\b{re.escape(a)}(?:s|es)?\b")) for a in aliases]

    def category_of(self, name: str | None) -> str | None:
        s = self.subjects.get(name) if name else None
        return s.category if s else None

    def count(self, name: str, text: str) -> int:
        """Mentions of one subject; longer aliases are consumed first so 'vulpes vulpes' counts once."""
        text, total = text.lower(), 0
        for _, pat in self._patterns[name]:
            total += len(pat.findall(text))
            text = pat.sub(" ", text)
        return total

    def canonicalize(self, text: str | None) -> str | None:
        """Free text -> canonical subject name, preferring the longest alias that matches."""
        if not text:
            return None
        text, best = text.lower(), None
        for name, pats in self._patterns.items():
            for alias, pat in pats:
                if pat.search(text) and (best is None or len(alias) > best[0]):
                    best = (len(alias), name)
        return best[1] if best else None

    def post_subjects(self, title: str, body: str, ratio: float = 0.5) -> dict[str, float]:
        """Subjects a post is about (title counts 3x). A post may legitimately be about several."""
        scores = {n: 3 * self.count(n, title) + self.count(n, body) for n in self.subjects}
        top = max(scores.values(), default=0)
        if top == 0:
            return {}
        return {n: float(s) for n, s in scores.items() if s >= ratio * top}


@lru_cache(maxsize=4)
def load_taxonomy(path: str) -> Taxonomy:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return Taxonomy([Subject(s["name"], s["category"], tuple(s.get("aliases", []))) for s in data["subjects"]])
