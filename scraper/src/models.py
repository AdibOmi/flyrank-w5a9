"""The shape of a finished record. Nothing reaches books.json without passing this."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class Book(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    # Identity + provenance
    product_url: str = Field(pattern=r"^https://books\.toscrape\.com/catalogue/[^\s?#]+/index\.html$")
    source_page: str = Field(pattern=r"^https://books\.toscrape\.com/catalogue/page-\d+\.html$")
    fetched_at: datetime = Field(strict=False)  # accept the ISO string from the fetcher

    # Scraped facts: raw text and clean value side by side
    title: str = Field(min_length=1)
    price_text: str
    price_gbp: float = Field(ge=0)
    availability_text: str
    in_stock: bool
    stock_count: int | None = Field(default=None, ge=0)
    rating_text: Literal["One", "Two", "Three", "Four", "Five"]
    rating: int = Field(ge=1, le=5)
    description: str | None = None

    @field_serializer("fetched_at")
    def _iso_utc(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
