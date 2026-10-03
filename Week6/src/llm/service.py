import json
import logging
import random
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Optional, Tuple

from fastapi import HTTPException
from openai import APIConnectionError, APIStatusError, APITimeoutError
from pydantic import ValidationError

from .. import config
from .client import build_client
from .schema import EnrichRequest, EnrichResponse

logger = logging.getLogger("llm")
logging.basicConfig(level=logging.INFO)

PROMPT_PATH = Path(__file__).resolve().parent.parent.parent / "prompts" / f"enrich-{config.PROMPT_VERSION}.md"
QUARANTINE_PATH = Path(__file__).resolve().parent.parent.parent / "logs" / "quarantine.jsonl"

_client = build_client()
_SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)

MAX_ATTEMPTS = 3  # 1 initial call + up to 2 retries, on retryable errors only


def _extract_json_object(text: str) -> str:
    fence_match = _JSON_FENCE_RE.search(text)
    if fence_match:
        return fence_match.group(1)
    object_match = _JSON_OBJECT_RE.search(text)
    if object_match:
        return object_match.group(0)
    return text


def _retry_after_seconds(exc: APIStatusError) -> Optional[float]:
    """Reads a Retry-After header (seconds or HTTP date). Returns None if absent/unparseable."""
    value = exc.response.headers.get("retry-after")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            return max(0.0, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError):
            return None


def _call_model(messages: list) -> Tuple[str, dict, int]:
    """Calls the model with a timeout and a bounded retry policy.
    Retries ONLY on timeouts, connection errors, 429 and 5xx. Every other 4xx (400/401/403/404/...)
    fails immediately, because it will not fix itself and every call burns quota."""
    last_error: Optional[Exception] = None
    timed_out = False
    for attempt in range(1, MAX_ATTEMPTS + 1):
        start = time.monotonic()
        wait: Optional[float] = None
        try:
            response = _client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=messages,
                temperature=0.2,
            )
            duration_ms = int((time.monotonic() - start) * 1000)
            content = response.choices[0].message.content if response.choices else ""
            usage = {
                "input_tokens": getattr(response.usage, "prompt_tokens", None),
                "output_tokens": getattr(response.usage, "completion_tokens", None),
            }
            return content or "", usage, duration_ms
        except APITimeoutError as exc:
            last_error, timed_out = exc, True
        except APIConnectionError as exc:
            last_error, timed_out = exc, False
        except APIStatusError as exc:
            if exc.status_code == 401:
                raise HTTPException(status_code=502, detail="LLM provider rejected our API key (401), not retrying.") from exc
            if exc.status_code != 429 and exc.status_code < 500:
                raise HTTPException(
                    status_code=502, detail=f"LLM request rejected ({exc.status_code}), not retrying."
                ) from exc
            last_error, timed_out = exc, False
            if exc.status_code == 429:
                wait = _retry_after_seconds(exc)

        if attempt < MAX_ATTEMPTS:
            backoff = wait if wait is not None else (2 ** (attempt - 1)) + random.uniform(0, 1)
            backoff = min(backoff, 30.0)
            logger.info("llm call failed (attempt %s/%s), retrying in %.1fs", attempt, MAX_ATTEMPTS, backoff)
            time.sleep(backoff)

    if timed_out:
        raise HTTPException(status_code=504, detail="LLM call timed out after retries.") from last_error
    raise HTTPException(status_code=502, detail="LLM provider unavailable after retries.") from last_error


def _parse_and_validate(raw_text: str) -> EnrichResponse:
    candidate = _extract_json_object(raw_text)
    data = json.loads(candidate)  # raises json.JSONDecodeError on failure
    return EnrichResponse.model_validate(data)  # raises pydantic.ValidationError on failure


def _quarantine(record: EnrichRequest, raw_text: str, error: str) -> None:
    QUARANTINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": config.PROMPT_VERSION,
        "input": record.model_dump(),
        "raw_model_output": raw_text,
        "error": error,
    }
    with QUARANTINE_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def _log_cost(model: str, usage: dict, duration_ms: int, repaired: bool) -> None:
    logger.info(
        json.dumps(
            {
                "event": "llm_call",
                "prompt_version": config.PROMPT_VERSION,
                "model": model,
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
                "duration_ms": duration_ms,
                "repaired": repaired,
            }
        )
    )


def _stub_response() -> EnrichResponse:
    return EnrichResponse(
        category="other",
        summary="Stub response for testing — no model was called.",
        quality_flags=["none"],
        confidence=0.5,
    )


def _fallback_response() -> EnrichResponse:
    return EnrichResponse(
        category="other",
        summary="LLM enrichment is currently disabled.",
        quality_flags=["llm_disabled"],
        confidence=0.0,
    )


def enrich(record: EnrichRequest) -> EnrichResponse:
    if not config.LLM_ENABLED:
        return _fallback_response()

    if config.LLM_STUB:
        return _stub_response()

    user_payload = json.dumps(record.model_dump())
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_payload},
    ]

    raw_text, usage, duration_ms = _call_model(messages)

    try:
        result = _parse_and_validate(raw_text)
        _log_cost(config.LLM_MODEL, usage, duration_ms, repaired=False)
        return result
    except (json.JSONDecodeError, ValidationError) as first_error:
        _log_cost(config.LLM_MODEL, usage, duration_ms, repaired=False)
        repair_messages = messages + [
            {"role": "assistant", "content": raw_text},
            {
                "role": "user",
                "content": (
                    "Your previous answer was rejected for this reason: "
                    f"{first_error}. Return only corrected JSON matching the schema."
                ),
            },
        ]
        repaired_text, repaired_usage, repaired_duration_ms = _call_model(repair_messages)

        try:
            result = _parse_and_validate(repaired_text)
            _log_cost(config.LLM_MODEL, repaired_usage, repaired_duration_ms, repaired=True)
            return result
        except (json.JSONDecodeError, ValidationError) as second_error:
            _quarantine(record, repaired_text, str(second_error))
            _log_cost(config.LLM_MODEL, repaired_usage, repaired_duration_ms, repaired=True)
            raise HTTPException(
                status_code=422,
                detail="Model output could not be validated against the schema, even after one repair attempt.",
            ) from second_error
