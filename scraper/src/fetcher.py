"""Polite fetching: identify ourselves, time out, go slowly, check status, cache everything."""

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

from . import config


class FetchError(Exception):
    """A page that could not be fetched."""

    def __init__(self, url: str, reason: str, status: int | None = None):
        super().__init__(reason)
        self.url = url
        self.reason = reason
        self.status = status


@dataclass
class Page:
    url: str
    html: str
    fetched_at: str  # ISO-8601 UTC time of the real network fetch (kept even on cache hits)
    from_cache: bool
    size: int


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class PoliteFetcher:
    def __init__(self, cache_dir: Path = config.CACHE_DIR, delay: float = config.DELAY_SECONDS):
        self.cache_dir = cache_dir
        self.delay = delay
        self.session = requests.Session()
        self.session.headers["User-Agent"] = config.USER_AGENT
        self._last_request = 0.0
        self.stats = {"pages_fetched": 0, "cache_hits": 0}

    def get(self, url: str, cache_name: str) -> Page:
        """Return the page from cache if we have it, otherwise fetch it once and cache it."""
        if urlparse(url).hostname != config.ALLOWED_HOST:
            raise FetchError(url, f"refusing to fetch outside {config.ALLOWED_HOST}")

        html_path = self.cache_dir / cache_name
        meta_path = html_path.with_suffix(".meta.json")
        if html_path.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            html = html_path.read_text(encoding="utf-8")
            self.stats["cache_hits"] += 1
            return Page(url, html, meta["fetched_at"], True, len(html.encode("utf-8")))

        body, fetched_at = self._fetch_once(url)
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_bytes(body)
        meta = {"url": url, "status": 200, "fetched_at": fetched_at, "bytes": len(body)}
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        # The server sends no charset, so requests would guess Latin-1 and turn "£" into "Â£".
        # The pages are UTF-8, so decode the raw bytes ourselves.
        return Page(url, body.decode("utf-8"), fetched_at, False, len(body))

    def _wait_politely(self) -> None:
        # Only real requests wait; cache hits never leave this computer.
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

    def _fetch_once(self, url: str) -> tuple[bytes, str]:
        self._wait_politely()
        fetched_at = utc_now_iso()
        try:
            response = self.session.get(url, timeout=config.TIMEOUT_SECONDS)
        finally:
            self._last_request = time.monotonic()
            self.stats["pages_fetched"] += 1
        # Only 200 means "here is your page". Anything else is a failed fetch, not HTML to parse.
        if response.status_code != 200:
            raise FetchError(url, f"HTTP {response.status_code}", status=response.status_code)
        return response.content, fetched_at
