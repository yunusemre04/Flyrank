from pathlib import Path

BASE_URL = "https://books.toscrape.com/"
START_CATALOGUE_URL = "https://books.toscrape.com/catalogue/page-1.html"
ROBOTS_URL = "https://books.toscrape.com/robots.txt"
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/flyrank/scraper)"
REQUEST_TIMEOUT = 10
POLITENESS_DELAY = 0.5
RETRY_DELAY = 1.0
CATALOGUE_PAGE_COUNT = 3

ROOT_DIR = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT_DIR / "cache"
OUTPUT_DIR = ROOT_DIR / "output"


def ensure_directories() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
