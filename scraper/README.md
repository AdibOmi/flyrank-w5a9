# The polite scraper (FlyRank A9)

A small, polite scraping pipeline for [Books to Scrape](https://books.toscrape.com/). It reads the first 3 catalogue pages, visits all 60 book pages, and turns the HTML into validated JSON.

**Lane:** Python (Requests + Beautiful Soup + Pydantic).

> Work in progress: this README grows one stage at a time.

## Run it

You need Python 3.10 or newer.

```powershell
cd scraper
py -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m src.main
```

The script starts at catalogue page 1 and follows the site's own "next" link to pages 2 and 3, then stops. It prints `catalogue_pages=3 discovered=60 unique_urls=60`.

Each page is fetched once (`FETCH`) and saved to `cache/`. Every run after that prints `CACHE HIT` and reads the saved copy, so the site only serves each page once. Real requests are spaced at least 1 s apart. Cache hits don't wait, because they never leave your computer.

It then opens all 60 book pages and extracts one raw record per book, printing `detail_pages=60` and one sample:

```json
{
  "title": "A Light in the Attic",
  "product_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "price_text": "£51.77",
  "availability_text": "In stock (22 available)",
  "rating_text": "Three",
  "description": "It's hard to imagine a world without A Light in the Attic. ...",
  "source_page": "https://books.toscrape.com/catalogue/page-1.html",
  "fetched_at": "2026-09-24T11:00:17Z"
}
```

- The selectors only look inside the product area of the page, so a second price elsewhere on the page can't be picked up by mistake.
- A book with no description gets `null`. Text is never made up.
- `source_page` and `fetched_at` are provenance: where the link was found and when the page was really fetched. A cache hit keeps the original fetch time.

## Record schema

Every raw record is normalized, then checked against [`src/models.py`](src/models.py) (Pydantic in strict mode with `extra="forbid"`) before it is stored. Each raw text value is stored next to its cleaned value.

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `product_url` | string | yes | Canonical identity: an absolute `https://books.toscrape.com/catalogue/.../index.html` URL with no query string or fragment |
| `source_page` | string | yes | Provenance: the catalogue page where the link was found |
| `fetched_at` | ISO-8601 UTC | yes | Provenance: when the page was actually fetched from the network |
| `title` | string | yes | Must not be empty |
| `price_text` | string | yes | Raw text, e.g. `"£51.77"` |
| `price_gbp` | number ≥ 0 | yes | Cleaned value, e.g. `51.77` |
| `availability_text` | string | yes | Raw text, e.g. `"In stock (22 available)"` |
| `in_stock` | boolean | yes | Cleaned value |
| `stock_count` | integer ≥ 0 or null | no | `22`, or null when the page doesn't say |
| `rating_text` | `"One"` to `"Five"` | yes | Raw value from the CSS class |
| `rating` | integer 1 to 5 | yes | Cleaned value |
| `description` | string or null | no | `null` when the page has no description |

Output:

| File | Contents |
| --- | --- |
| `output/books.json` | The validated records |
| `output/errors.json` | Records that failed the schema, with field-level reasons and their raw values (`[]` on a clean run). They never reach `books.json`. |

**Reruns are safe.** Records are keyed by `product_url`, so a book that shows up twice is stored once. Both files are rewritten from scratch on every run (through a temp file and a rename), so a second run gives the same 60 records, not 120.

## Target classification

| Question | Answer |
| --- | --- |
| **Which site** | `books.toscrape.com` only. |
| **Why** | [toscrape.com](https://toscrape.com/) describes it as *"A fictional bookstore that desperately wants to be scraped. It's a safe place for beginners learning web scraping and for developers validating their scraping technologies as well."* It is a practice sandbox. The shop, prices and stock are fictional, and no real business or person is affected. |
| **How much** | The first 3 catalogue pages (`page-1.html` to `page-3.html`) and the 60 book pages they link to. That is 63 requests on a cold run. |
| **What data** | For each book: title, product URL, price, availability, star rating, description, plus provenance (which catalogue page it was found on and when it was fetched). No personal data exists on the site, and none is collected. |
| **robots.txt** | I requested `https://books.toscrape.com/robots.txt` once on 2026-09-24. It returned **HTTP 404, so no robots file was found**. A missing file is not permission. Permission comes from the sandbox statement above. |
| **Why this is appropriate** | The site exists so people can practise scraping on it, and this scraper takes a small, fixed slice of it slowly, with an honest user-agent and a local cache. |

I will not reuse this code on another site without checking its rules and terms first.
