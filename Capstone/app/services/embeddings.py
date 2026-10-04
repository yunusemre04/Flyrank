import time

from ..errors import ProviderError
from ..providers.base import Usage
from ..schemas import ImageTags


def image_text(tags: ImageTags) -> str:
    """What we embed for an image: the caption plus the structured tags."""
    attrs = ", ".join(tags.attributes)
    return f"{tags.caption}. Subject: {tags.subject}. Category: {tags.category}. Attributes: {attrs}"


def post_text(title: str, body: str) -> str:
    return f"{title}. {body}"[:8000]


def embed_text(provider, text: str, settings, rec, image_id: int | None = None, post_id: int | None = None) -> list[float]:
    for attempt in range(1, settings.max_attempts + 1):
        rec.check()
        try:
            vec, usage = provider.embed(text)
        except ProviderError as e:
            rec.record("embedding", Usage(), ok=False, image_id=image_id, post_id=post_id)
            if not e.retriable or attempt == settings.max_attempts:
                raise
            time.sleep(settings.retry_base_delay * 2 ** (attempt - 1))
            continue
        if not vec or not all(isinstance(x, (int, float)) for x in vec):
            rec.record("embedding", usage, ok=False, image_id=image_id, post_id=post_id)
            raise ProviderError("embedding response was empty or non-numeric", retriable=False)
        rec.record("embedding", usage, ok=True, image_id=image_id, post_id=post_id)
        return [float(x) for x in vec]
    raise ProviderError("unreachable")
