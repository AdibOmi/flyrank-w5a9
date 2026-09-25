"""Entry point for the polite scraper. Run from the scraper/ folder:  python -m src.main"""

from urllib.parse import urlparse

from . import config
from .fetcher import FetchError, PoliteFetcher


def cache_name_for(url: str) -> str:
    """catalogue/page-1.html -> catalogue-page-1.html"""
    parts = [p for p in urlparse(url).path.split("/") if p]
    return "-".join(parts)


def log_page(page, label: str) -> None:
    status = "CACHE HIT" if page.from_cache else "FETCH    "
    print(f"{status} {label:<60} {page.size:>7,} bytes")


def main() -> None:
    fetcher = PoliteFetcher()
    name = cache_name_for(config.START_URL)
    try:
        page = fetcher.get(config.START_URL, name)
    except FetchError as err:
        print(f"FAILED    {config.START_URL} -> {err.reason}")
        raise SystemExit(1)
    log_page(page, name)


if __name__ == "__main__":
    main()
