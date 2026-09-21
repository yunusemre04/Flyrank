import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from pydantic import ValidationError

from .config import (
    CATALOGUE_PAGE_COUNT,
    CACHE_DIR,
    OUTPUT_DIR,
    ROBOTS_URL,
    START_CATALOGUE_URL,
    ensure_directories,
)
from .fetcher import fetch_html, get_network_request_count, reset_network_request_count
from .models import BookRecord, ValidationErrorRecord
from .parser import extract_book_details, extract_catalogue_page, price_to_float


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def detail_cache_filename(url: str) -> str:
    path = Path(urlparse(url).path.rstrip("/"))
    slug = path.parent.name if path.name in {"index.html", ""} else path.stem
    slug = slug or "index"
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", slug)
    return f"detail-{slug}.html"


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run(test_failure: bool = False) -> dict:
    ensure_directories()
    reset_network_request_count()
    start = time.monotonic()
    start_time = utc_now()
    cache_hits = 0
    failed_pages = 0
    errors: list[dict] = []

    try:
        _, is_cache_hit = fetch_html(ROBOTS_URL, "robots.txt")
        cache_hits += int(is_cache_hit)
        robots_status = "checked"
    except Exception as error:
        if getattr(error, "response", None) is not None and error.response.status_code == 404:
            robots_status = "no robots file found"
        else:
            robots_status = f"check failed: {error}"
            failed_pages += 1

    book_urls: list[str] = []
    source_pages: dict[str, str] = {}
    current_url = START_CATALOGUE_URL
    catalogue_pages_fetched = 0
    for page_number in range(1, CATALOGUE_PAGE_COUNT + 1):
        try:
            html, is_cache_hit = fetch_html(current_url, f"catalogue-page-{page_number}.html")
            cache_hits += int(is_cache_hit)
            catalogue_pages_fetched += 1
            page_urls, next_url = extract_catalogue_page(html, current_url)
            book_urls.extend(page_urls)
            for product_url in page_urls:
                source_pages.setdefault(product_url, current_url)
            if not next_url:
                break
            current_url = next_url
        except Exception as error:
            failed_pages += 1
            errors.append({"record": {"source_page": current_url}, "error": str(error), "timestamp": utc_now()})
            break

    unique_urls = list(dict.fromkeys(book_urls))
    if test_failure:
        unique_urls.append("https://books.toscrape.com/catalogue/non-existent-book_9999/index.html")

    records_by_url: dict[str, dict] = {}
    invalid_records = 0
    for product_url in unique_urls:
        try:
            html, is_cache_hit = fetch_html(product_url, detail_cache_filename(product_url))
            cache_hits += int(is_cache_hit)
            raw_record = extract_book_details(html, product_url, source_pages.get(product_url, current_url), utc_now())
            normalized = {**raw_record, "price_gbp": price_to_float(raw_record["price_text"])}
            record = BookRecord.model_validate(normalized)
            records_by_url[record.product_url] = record.model_dump()
        except ValidationError as error:
            invalid_records += 1
            errors.append(ValidationErrorRecord(record=locals().get("raw_record", {"product_url": product_url}), error=str(error), timestamp=utc_now()).model_dump())
        except Exception as error:
            failed_pages += 1
            errors.append({"record": {"product_url": product_url}, "error": str(error), "timestamp": utc_now()})

    records = list(records_by_url.values())
    write_json(OUTPUT_DIR / "books.json", records)
    if errors:
        write_json(OUTPUT_DIR / "errors.json", errors)
    else:
        write_json(OUTPUT_DIR / "errors.json", [])

    report = {
        "start_time": start_time,
        "duration_seconds": round(time.monotonic() - start, 3),
        "pages_fetched": get_network_request_count(),
        "cache_hits": cache_hits,
        "valid_records": len(records),
        "invalid_records": invalid_records,
        "failed_pages": failed_pages,
        "robots_status": robots_status,
        "catalogue_pages": catalogue_pages_fetched,
    }
    write_json(OUTPUT_DIR / "run-report.json", report)
    print("\nScraper run summary")
    print("-------------------")
    for key in ("pages_fetched", "cache_hits", "valid_records", "invalid_records", "failed_pages"):
        print(f"{key:18} {report[key]}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Polite Books to Scrape pipeline")
    parser.add_argument("--test-failure", action="store_true", help="include one intentionally missing detail URL")
    args = parser.parse_args()
    sys.exit(0 if run(test_failure=args.test_failure) else 1)
