"""Extraction: turn HTML into raw text fields. No cleaning happens here -- that is normalize.py's job."""

from urllib.parse import urljoin

from bs4 import BeautifulSoup

RATING_WORDS = ("One", "Two", "Three", "Four", "Five")


def clean_text(value: str | None) -> str | None:
    """Collapse runs of whitespace; empty strings become None."""
    if value is None:
        return None
    text = " ".join(value.split())
    return text or None


def parse_catalogue(html: str, page_url: str) -> tuple[list[str], str | None]:
    """Return (absolute book URLs on this page, absolute URL of the next page or None).

    Links on the page are relative (e.g. "a-light-in-the-attic_1000/index.html"), so they are
    resolved against the page's own URL with urljoin -- never by gluing strings together.
    """
    soup = BeautifulSoup(html, "html.parser")
    book_urls = []
    for link in soup.select("article.product_pod h3 a[href]"):
        book_urls.append(urljoin(page_url, link["href"]))

    next_link = soup.select_one("ul.pager li.next a[href]")
    next_url = urljoin(page_url, next_link["href"]) if next_link else None
    return book_urls, next_url


def parse_book(html: str, product_url: str, source_page: str, fetched_at: str) -> dict:
    """Extract the eight raw fields from a book detail page.

    Selectors are scoped to the product area (div.product_main / #product_description),
    so a second price elsewhere on the page can never be picked up by mistake.
    Missing values come back as None -- nothing is invented.
    """
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("article.product_page div.product_main")
    if main is None:
        raise ValueError("product area (article.product_page div.product_main) not found")

    title = main.select_one("h1")
    price = main.select_one("p.price_color")
    availability = main.select_one("p.availability")

    rating_text = None
    rating = main.select_one("p.star-rating")
    if rating is not None:
        rating_text = next((c for c in rating.get("class", []) if c in RATING_WORDS), None)

    description = None
    heading = soup.select_one("article.product_page #product_description")
    if heading is not None:
        paragraph = heading.find_next_sibling("p")
        if paragraph is not None:
            description = clean_text(paragraph.get_text())

    return {
        "title": clean_text(title.get_text()) if title else None,
        "product_url": product_url,
        "price_text": clean_text(price.get_text()) if price else None,
        "availability_text": clean_text(availability.get_text()) if availability else None,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at,
    }
