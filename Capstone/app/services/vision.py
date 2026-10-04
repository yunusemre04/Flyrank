import time

from pydantic import ValidationError

from ..errors import InvalidModelOutput, ProviderError
from ..providers.base import Usage
from ..schemas import ImageTags


def build_prompt(tax) -> str:
    return (
        "You are cataloguing a stock-photo library. Look at the image and describe its single main subject.\n"
        "Return JSON with: subject (specific, e.g. 'red fox' or 'gray wolf', never just 'animal'), "
        f"category (one of: {', '.join(tax.categories)}, other), attributes (3-6 short visual descriptors), "
        "caption (one factual sentence), confidence (0-1, your honest certainty about the subject; "
        "use below 0.5 if the image is blurry, ambiguous or shows several competing subjects)."
    )


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[4:] if raw.lower().startswith("json") else raw
    return raw.strip()


def tag_image(provider, data: bytes, mime: str, filename: str, tax, settings, rec, image_id: int) -> ImageTags:
    """Vision call -> schema validation -> retry. Invalid output is never trusted."""
    prompt = build_prompt(tax)
    if provider.name == "mock":  # only the offline test double may see filenames; real models never do
        prompt += f"\nFILENAME_HINT={filename}"
    feedback, last = "", "no attempt made"
    for attempt in range(1, settings.max_attempts + 1):
        rec.check()
        try:
            raw, usage = provider.describe_image(data, mime, prompt + feedback)
        except ProviderError as e:
            rec.record("vision", Usage(), ok=False, image_id=image_id)
            last = str(e)
            if not e.retriable or attempt == settings.max_attempts:
                raise
            time.sleep(settings.retry_base_delay * 2 ** (attempt - 1))
            continue
        try:
            tags = ImageTags.model_validate_json(_strip_fences(raw))
        except ValidationError as e:
            rec.record("vision", usage, ok=False, image_id=image_id)
            last = "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()[:3])
            feedback = f"\nYour previous answer was invalid JSON for the schema ({last}). Return ONLY valid JSON."
            continue
        rec.record("vision", usage, ok=True, image_id=image_id)
        return tags
    raise InvalidModelOutput(f"vision output invalid after {settings.max_attempts} attempts: {last}")
