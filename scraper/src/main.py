"""Entry point for the polite scraper. Run from the scraper/ folder:  python -m src.main"""

import json
from pathlib import Path
from urllib.parse import urlparse

from pydantic import ValidationError

from . import config
from .fetcher import FetchError, PoliteFetcher
from .models import Book
from .normalize import canonical_url, normalize
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


def write_json(path: Path, data) -> None:
    """Write via a temp file so a crash mid-write never leaves half a JSON file behind."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


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

    # Remove duplicates by canonical URL; the first sighting keeps its source page.
    unique: dict[str, str] = {}
    for book_url, source_page in found:
        unique.setdefault(canonical_url(book_url), source_page)

    print(f"catalogue_pages={catalogue_pages} discovered={len(found)} unique_urls={len(unique)}")

    # Visit every book page (same politeness as Stage 1: user-agent, timeout, status check, delay, cache).
    books: dict[str, dict] = {}
    errors: list[dict] = []
    detail_pages, sample = 0, None
    for book_url, source_page in unique.items():
        name = cache_name_for(book_url)
        page = fetcher.get(book_url, name)
        log_page(page, name)
        # Provenance: where the link was found and when the page was really fetched.
        raw = parse_book(page.html, book_url, source_page, page.fetched_at)
        detail_pages += 1
        sample = sample or raw

        # Normalize and validate before anything is stored.
        try:
            book = Book.model_validate(normalize(raw))
        except ValidationError as err:
            reasons = [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in err.errors()]
            errors.append({"url": book_url, "stage": "validate", "reasons": reasons, "raw": raw})
            print(f"INVALID   {name:<60} {'; '.join(reasons)}")
            continue
        books[book.product_url] = book.model_dump(mode="json")  # keyed by identity: no duplicates

    print(f"detail_pages={detail_pages}")
    print(f"pages_fetched={fetcher.stats['pages_fetched']} cache_hits={fetcher.stats['cache_hits']}")
    if sample:
        print("sample raw record:")
        print(json.dumps(sample, indent=2, ensure_ascii=False))

    # Store. Files are rewritten from scratch, so a rerun gives the same 60 records, not 120.
    write_json(config.OUTPUT_DIR / "books.json", list(books.values()))
    write_json(config.OUTPUT_DIR / "errors.json", errors)
    print(f"valid_records={len(books)} invalid_records={len(errors)}")


if __name__ == "__main__":
    main()
