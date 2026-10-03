from openai import OpenAI

from .. import config


def build_client() -> OpenAI:
    return OpenAI(
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY or "unused",
        timeout=config.LLM_TIMEOUT_SECONDS,
        max_retries=0,  # we implement our own retry policy in service.py
    )
