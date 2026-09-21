# Week 5: Polite Book Scraper

## Target classification

This is a sandbox collection exercise against [Books to Scrape](https://books.toscrape.com/). The scope is exactly the first three catalogue pages, which contain 60 books. The pipeline checks `robots.txt` once at startup and records whether it was available; a missing 404 robots file is handled gracefully.

I will not reuse this code on another site without checking its rules and terms first.

## Quickstart

From the `Week5/scraper` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m src.main
```

The run writes `output/books.json`, `output/errors.json`, and `output/run-report.json`. To exercise fault tolerance, run `python -m src.main --test-failure`. The first run takes a few minutes because requests are deliberately spaced; later runs use the local cache.

## Politeness rules implemented

- Identifying User-Agent: `FlyRankInternship-A9/1.0 (+https://github.com/flyrank/scraper)`
- At least 500 ms before every real request
- 10-second request timeout
- One retry after a timeout or 5xx response, with a one-second retry wait
- Local file cache; cached responses do not incur a delay

## Record schema

Each `BookRecord` contains `title: str`, absolute HTTPS `product_url: str`, `price_text: str`, `availability_text: str`, `rating_text: str`, optional `description: str | None`, `source_page: str`, `fetched_at: str`, and normalized `price_gbp: float`. Pydantic v2 validates the structure and rejects non-HTTPS product URLs. Price normalization extracts a numeric GBP value from the displayed price.

## Sample run report

```json
{
  "start_time": "2026-09-21T10:00:00+00:00",
  "duration_seconds": 34.217,
  "pages_fetched": 64,
  "cache_hits": 0,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 0
}
```

## No-browser justification

The server serves the catalogue and product details as fully rendered HTML. `requests` plus BeautifulSoup can retrieve and parse the required data directly, so a headless browser would add unnecessary overhead and complexity.

## Scraping ethics

Prefer an official API when one exists. Identify the client honestly, honor robots rules and terms, use conservative rate limits, cache responses, collect only what is necessary, and stop when a site asks you to stop. Do not reuse this pipeline against another domain without reviewing that domain's policies first.
