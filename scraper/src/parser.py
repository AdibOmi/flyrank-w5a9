"""Extraction: turn HTML into raw values. No cleaning happens here."""

from urllib.parse import urljoin

from bs4 import BeautifulSoup


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
