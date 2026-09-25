"""Entry point: fetch -> extract -> normalize -> validate -> store -> report.

Run from the scraper/ folder:  python -m src.main
"""

import argparse
import json
import time
from pathlib import Path
from urllib.parse import urlparse

from pydantic import ValidationError

from . import config
from .fetcher import FetchError, PoliteFetcher, utc_now_iso
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


def discover(fetcher: PoliteFetcher, failures: list) -> tuple[int, list[tuple[str, str]]]:
    """Follow the site's own "next" links for MAX_CATALOGUE_PAGES pages. Returns (pages, [(book_url, source_page)])."""
    found = []
    url, pages = config.START_URL, 0
    while url and pages < config.MAX_CATALOGUE_PAGES:
        try:
            page = fetcher.get(url, cache_name_for(url))
        except FetchError as err:
            failures.append({"url": url, "stage": "catalogue", "reason": err.reason, "attempts": err.attempts})
            print(f"FAILED    {url} -> {err.reason}")
            break
        log_page(page, cache_name_for(url))
        pages += 1
        book_urls, url = parse_catalogue(page.html, page.url)
        found.extend((book_url, page.url) for book_url in book_urls)
    return pages, found


def run(fake_url: bool, show_sample: bool) -> dict:
    started_at, t0 = utc_now_iso(), time.monotonic()
    fetcher = PoliteFetcher()
    failures: list[dict] = []
    errors: list[dict] = []

    # 1. Discover book URLs, de-duplicated by canonical URL (first sighting keeps its source page).
    catalogue_pages, found = discover(fetcher, failures)
    unique: dict[str, str] = {}
    for book_url, source_page in found:
        unique.setdefault(canonical_url(book_url), source_page)
    print(f"catalogue_pages={catalogue_pages} discovered={len(found)} unique_urls={len(unique)}")

    if fake_url:
        unique.setdefault(config.FAKE_BOOK_URL, config.START_URL)
        print(f"added deliberately broken URL: {config.FAKE_BOOK_URL}")

    # 2. Visit every book page on its own -- one bad page is logged and skipped, never fatal.
    books: dict[str, dict] = {}
    detail_ok, sample = 0, None
    for book_url, source_page in unique.items():
        name = cache_name_for(book_url)
        try:
            page = fetcher.get(book_url, name)
            raw = parse_book(page.html, book_url, source_page, page.fetched_at)
        except FetchError as err:
            failures.append({"url": book_url, "stage": "fetch", "reason": err.reason, "attempts": err.attempts})
            print(f"FAILED    {name:<60} {err.reason}")
            continue
        except Exception as err:  # malformed HTML must not take the run down either
            failures.append({"url": book_url, "stage": "extract", "reason": f"{type(err).__name__}: {err}"})
            print(f"FAILED    {name:<60} extract: {err}")
            continue
        log_page(page, name)
        detail_ok += 1
        sample = sample or raw

        # 3. Normalize and validate before anything is stored.
        try:
            book = Book.model_validate(normalize(raw))
        except ValidationError as err:
            reasons = [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in err.errors()]
            errors.append({"url": book_url, "stage": "validate", "reasons": reasons, "raw": raw})
            print(f"INVALID   {name:<60} {'; '.join(reasons)}")
            continue
        books[book.product_url] = book.model_dump(mode="json")  # keyed by identity: no duplicates

    print(f"detail_pages={detail_ok}")
    if show_sample and sample:
        print("sample raw record:")
        print(json.dumps(sample, indent=2, ensure_ascii=False))

    # 4. Store. Files are rewritten from scratch, so a rerun gives the same 60 records, not 120.
    write_json(config.OUTPUT_DIR / "books.json", list(books.values()))
    write_json(config.OUTPUT_DIR / "errors.json", errors)

    # 5. Report.
    report = {
        "started_at": started_at,
        "finished_at": utc_now_iso(),
        "duration_seconds": round(time.monotonic() - t0, 2),
        "catalogue_pages": catalogue_pages,
        "discovered_urls": len(found),
        "unique_urls": len(unique),
        "detail_pages": detail_ok,
        "pages_fetched": fetcher.stats["pages_fetched"],
        "cache_hits": fetcher.stats["cache_hits"],
        "retries": fetcher.stats["retries"],
        "valid_records": len(books),
        "invalid_records": len(errors),
        "failed_pages": len(failures),
        "failures": failures,
    }
    write_json(config.OUTPUT_DIR / "run-report.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Polite scraper for the first 3 catalogue pages of books.toscrape.com")
    parser.add_argument("--fake-url", action="store_true",
                        help="add one made-up book URL to prove a broken page is skipped, not fatal")
    parser.add_argument("--no-sample", action="store_true", help="do not print a sample raw record")
    args = parser.parse_args()

    report = run(fake_url=args.fake_url, show_sample=not args.no_sample)
    summary = {k: v for k, v in report.items() if k != "failures"}
    print("run report:", json.dumps(summary))


if __name__ == "__main__":
    main()
