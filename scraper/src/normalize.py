"""Normalization: raw strings in, clean typed values out. Raw values are kept alongside."""

import re
from urllib.parse import urlsplit, urlunsplit

from .parser import RATING_WORDS

PRICE_RE = re.compile(r"^£\s*(\d+(?:\.\d{1,2})?)$")
STOCK_RE = re.compile(r"\((\d+)\s+available\)")


def parse_price(price_text: str | None) -> float | None:
    """'£51.77' -> 51.77. Anything that is not a clean pound price returns None (and fails validation)."""
    if not price_text:
        return None
    match = PRICE_RE.match(price_text.strip())
    return float(match.group(1)) if match else None


def parse_rating(rating_text: str | None) -> int | None:
    """'Three' -> 3."""
    if rating_text in RATING_WORDS:
        return RATING_WORDS.index(rating_text) + 1
    return None


def parse_stock(availability_text: str | None) -> tuple[bool | None, int | None]:
    """'In stock (22 available)' -> (True, 22)."""
    if not availability_text:
        return None, None
    in_stock = availability_text.lower().startswith("in stock")
    match = STOCK_RE.search(availability_text)
    return in_stock, int(match.group(1)) if match else (0 if not in_stock else None)


def canonical_url(url: str) -> str:
    """One stable identity per book: lower-case scheme and host, no query string or fragment."""
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, "", ""))


def normalize(raw: dict) -> dict:
    """Build the finished record: every raw field plus its clean counterpart."""
    in_stock, stock_count = parse_stock(raw.get("availability_text"))
    return {
        **raw,
        "product_url": canonical_url(raw["product_url"]),
        "price_gbp": parse_price(raw.get("price_text")),
        "in_stock": in_stock,
        "stock_count": stock_count,
        "rating": parse_rating(raw.get("rating_text")),
    }
