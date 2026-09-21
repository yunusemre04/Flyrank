import time
from pathlib import Path
from typing import Optional

import requests

from .config import CACHE_DIR, POLITENESS_DELAY, REQUEST_TIMEOUT, RETRY_DELAY, USER_AGENT

_network_request_count = 0


def reset_network_request_count() -> None:
    global _network_request_count
    _network_request_count = 0


def get_network_request_count() -> int:
    return _network_request_count


def fetch_html(url: str, cache_filename: Optional[str] = None) -> tuple[str, bool]:
    """Fetch HTML with a filesystem cache and one retry for transient failures."""
    filename = cache_filename or _default_cache_filename(url)
    cache_path = CACHE_DIR / filename
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8"), True

    global _network_request_count
    last_error: Optional[Exception] = None
    for attempt in range(2):
        time.sleep(POLITENESS_DELAY)
        try:
            _network_request_count += 1
            response = requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT,
            )
            if response.status_code == 200:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(response.text, encoding="utf-8")
                return response.text, False
            if response.status_code >= 500 and attempt == 0:
                time.sleep(RETRY_DELAY)
                continue
            response.raise_for_status()
            raise RuntimeError(f"Unexpected HTTP status {response.status_code} for {url}")
        except (requests.Timeout, requests.ConnectionError) as error:
            last_error = error
            if attempt == 0:
                time.sleep(RETRY_DELAY)
                continue
            raise
        except requests.HTTPError:
            raise

    raise RuntimeError(f"Request failed for {url}: {last_error}")


def _default_cache_filename(url: str) -> str:
    from urllib.parse import urlparse

    path = urlparse(url).path.strip("/").replace("/", "-") or "index"
    return f"{path}.html"
