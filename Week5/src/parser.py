import re
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def extract_catalogue_page(html: str, current_page_url: str) -> tuple[list[str], Optional[str]]:
    soup = BeautifulSoup(html, "html.parser")
    product_urls = []
    for link in soup.select("article.product_pod h3 a"):
        href = link.get("href")
        if href:
            product_urls.append(urljoin(current_page_url, href))

    next_link = soup.select_one("li.next a")
    next_url = urljoin(current_page_url, next_link["href"]) if next_link and next_link.get("href") else None
    return product_urls, next_url


def extract_book_details(html: str, product_url: str, source_page: str, fetched_at: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    rating = soup.select_one("p.star-rating")
    rating_text = ""
    if rating:
        rating_text = next((name for name in rating.get("class", []) if name != "star-rating"), "")

    description_tag = soup.select_one("#product_description ~ p")
    return {
        "title": _clean_text(soup.select_one("h1").get_text()) if soup.select_one("h1") else "",
        "product_url": product_url,
        "price_text": _clean_text(soup.select_one(".product_main .price_color").get_text()) if soup.select_one(".product_main .price_color") else "",
        "availability_text": _clean_text(soup.select_one(".availability").get_text()) if soup.select_one(".availability") else "",
        "rating_text": rating_text,
        "description": _clean_text(description_tag.get_text()) if description_tag else None,
        "source_page": source_page,
        "fetched_at": fetched_at,
    }


def price_to_float(price_text: str) -> float:
    match = re.search(r"\d+(?:\.\d+)?", price_text.replace(",", ""))
    if not match:
        raise ValueError(f"Could not extract a numeric price from {price_text!r}")
    return float(match.group())
