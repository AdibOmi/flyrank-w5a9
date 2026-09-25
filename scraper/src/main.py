"""Entry point for the polite scraper. Run from the scraper/ folder:  python -m src.main"""

import json
from urllib.parse import urlparse

from . import config
from .fetcher import FetchError, PoliteFetcher
from .parser import parse_book, parse_catalogue


def cache_name_for(url: str) -> str:
    """catalogue/page-1.html -> catalogue-page-1.html; catalogue/<slug>/index.html -> books/<slug>.html"""
    parts = [p for p in urlparse(url).path.split("/") if p]
    if parts[-1] == "index.html" and len(parts) >= 2:
        return f"books/{parts[-2]}.html"
    return "-".join(parts)


def log_page(page, label: str) -> None:
    status = "CACHE HIT" if page.from_cache else "FETCH    "
    print(f"{status} {label:<60} {page.size:>7,} bytes")


def discover(fetcher: PoliteFetcher) -> tuple[int, list[tuple[str, str]]]:
    """Follow the site's own "next" links for MAX_CATALOGUE_PAGES pages. Returns (pages, [(book_url, source_page)])."""
    found = []
    url, pages = config.START_URL, 0
    while url and pages < config.MAX_CATALOGUE_PAGES:
        try:
            page = fetcher.get(url, cache_name_for(url))
        except FetchError as err:
            print(f"FAILED    {url} -> {err.reason}")
            break
        log_page(page, cache_name_for(url))
        pages += 1
        book_urls, url = parse_catalogue(page.html, page.url)
        found.extend((book_url, page.url) for book_url in book_urls)
    return pages, found


def main() -> None:
    fetcher = PoliteFetcher()
    catalogue_pages, found = discover(fetcher)

    # Remove duplicates; the first sighting keeps its source page.
    unique: dict[str, str] = {}
    for book_url, source_page in found:
        unique.setdefault(book_url, source_page)

    print(f"catalogue_pages={catalogue_pages} discovered={len(found)} unique_urls={len(unique)}")

    # Visit every book page (same politeness as Stage 1: user-agent, timeout, status check, delay, cache).
    raw_records = []
    for book_url, source_page in unique.items():
        name = cache_name_for(book_url)
        page = fetcher.get(book_url, name)
        log_page(page, name)
        # Provenance: where the link was found and when the page was really fetched.
        raw_records.append(parse_book(page.html, book_url, source_page, page.fetched_at))

    print(f"detail_pages={len(raw_records)}")
    print(f"pages_fetched={fetcher.stats['pages_fetched']} cache_hits={fetcher.stats['cache_hits']}")
    if raw_records:
        print("sample raw record:")
        print(json.dumps(raw_records[0], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
