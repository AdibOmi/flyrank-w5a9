# The polite scraper (FlyRank A9)

A small, polite scraping pipeline for [Books to Scrape](https://books.toscrape.com/). It reads the first 3 catalogue pages, visits all 60 book pages, and turns the HTML into validated JSON. One broken page doesn't stop the run, and every run ends with a report.

```
fetch → extract → normalize → validate → store → report
```

**Lane:** Python (Requests + Beautiful Soup + Pydantic).

## Quick start (under 5 minutes)

You need Python 3.10 or newer.

```powershell
cd scraper
py -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m src.main
```

This writes:

| File | Contents |
| --- | --- |
| `output/books.json` | The 60 validated, unique book records |
| `output/errors.json` | Records that failed the schema, with the reasons (`[]` on a clean run) |
| `output/run-report.json` | What happened during the run |
| `cache/` | Raw HTML for every page fetched (git-ignored) |

The first run makes 63 real requests with a 1 s gap between them, so it takes about 1 min 40 s. Later runs read from `cache/` and finish in about a second.

Other commands:

```powershell
python -m src.main --fake-url    # add one made-up book URL to prove a bad page is skipped
python -m src.main --no-sample   # don't print the sample raw record
```

To fetch everything again from the site, delete the `cache/` folder.

## Target classification

| Question | Answer |
| --- | --- |
| **Which site** | `books.toscrape.com` only. The fetcher refuses any other host. |
| **Why** | [toscrape.com](https://toscrape.com/) describes it as *"A fictional bookstore that desperately wants to be scraped. It's a safe place for beginners learning web scraping and for developers validating their scraping technologies as well."* It is a practice sandbox. The shop, prices and stock are fictional, and no real business or person is affected. |
| **How much** | The first 3 catalogue pages (`page-1.html` to `page-3.html`) and the 60 book pages they link to. That is 63 requests on a cold run and none on a cached run. |
| **What data** | For each book: title, product URL, price, availability, star rating, description, plus provenance (which catalogue page it was found on and when it was fetched). No personal data exists on the site, and none is collected. |
| **robots.txt** | I requested `https://books.toscrape.com/robots.txt` once on 2026-09-24. It returned **HTTP 404, so no robots file was found**. A missing file is not permission. Permission comes from the sandbox statement above. |
| **Why this is appropriate** | The site exists so people can practise scraping on it, and this scraper takes a small, fixed slice of it slowly, with an honest user-agent and a local cache. |

I will not reuse this code on another site without checking its rules and terms first.

## Politeness rules

| Rule | How it is enforced (`src/config.py`, `src/fetcher.py`) |
| --- | --- |
| **Honest user-agent** | `FlyRankInternshipA9/1.0 (+https://github.com/AdibOmi/flyrank-w5a9)` is sent on every request |
| **Timeout** | 10 s per request |
| **Delay** | At least 1.0 s between real requests. The assignment minimum is 0.5 s. Cache hits never touch the network, so they need no delay. |
| **Status check** | Only `200` is treated as a page. Anything else raises a `FetchError` and is never parsed or cached. |
| **Cache** | Every successful response is saved to `cache/` with a `.meta.json` sidecar (URL, status, real fetch time). After that, the page is always read from disk. |
| **Retry** | One retry after 2 s, only for timeouts, connection errors and `5xx`. `404` and `403` are never retried. |
| **Scope** | Stops after 3 catalogue pages, found by following the site's own "next" link. No book URLs are hardcoded. |
| **Host lock** | Requests to any host other than `books.toscrape.com` are refused. |

## Record schema

Defined once in [`src/models.py`](src/models.py) with Pydantic in strict mode with `extra="forbid"`. Each raw text value is stored next to its cleaned value.

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `product_url` | string | yes | Canonical identity: an absolute `https://books.toscrape.com/catalogue/.../index.html` URL with no query string or fragment |
| `source_page` | string | yes | Provenance: the catalogue page where the link was found |
| `fetched_at` | ISO-8601 UTC | yes | Provenance: when the page was actually fetched from the network. A cache hit keeps the original time. |
| `title` | string | yes | Must not be empty |
| `price_text` | string | yes | Raw text, e.g. `"£51.77"` |
| `price_gbp` | number ≥ 0 | yes | Cleaned value, e.g. `51.77` |
| `availability_text` | string | yes | Raw text, e.g. `"In stock (22 available)"` |
| `in_stock` | boolean | yes | Cleaned value |
| `stock_count` | integer ≥ 0 or null | no | `22`, or null when the page doesn't say |
| `rating_text` | `"One"` to `"Five"` | yes | Raw value from the CSS class |
| `rating` | integer 1 to 5 | yes | Cleaned value |
| `description` | string or null | no | `null` when the page has no description. Text is never made up. |

Example record from `output/books.json` (description shortened here):

```json
{
  "product_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "source_page": "https://books.toscrape.com/catalogue/page-1.html",
  "fetched_at": "2026-09-24T11:00:17Z",
  "title": "A Light in the Attic",
  "price_text": "£51.77",
  "price_gbp": 51.77,
  "availability_text": "In stock (22 available)",
  "in_stock": true,
  "stock_count": 22,
  "rating_text": "Three",
  "rating": 3,
  "description": "It's hard to imagine a world without A Light in the Attic. ..."
}
```

**Validation and idempotency.** Every record passes through `Book.model_validate` before it is stored. A record that fails goes to `output/errors.json` with the field-level reasons and its raw values, and never reaches `books.json`. Records are keyed by `product_url`, and the output files are rewritten on every run (through a temp file and a rename). A second run therefore gives the same 60 records, not 120.

## Proof: a real run report

Below is the `output/run-report.json` from the first cold run on 2026-09-24:

```json
{
  "started_at": "2026-09-24T11:00:11Z",
  "finished_at": "2026-09-24T11:01:53Z",
  "duration_seconds": 102.03,
  "catalogue_pages": 3,
  "discovered_urls": 60,
  "unique_urls": 60,
  "detail_pages": 60,
  "pages_fetched": 63,
  "cache_hits": 0,
  "retries": 0,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 0,
  "failures": []
}
```

The rerun right after it was served entirely from cache: `pages_fetched: 0`, `cache_hits: 63`, `valid_records: 60`, 3.7 s.

The broken-page run used `--fake-url`, which adds `.../this-book-does-not-exist_99999/index.html`. It finished normally with `valid_records: 60` and `failed_pages: 1`. The failure was a single `404` with `attempts: 1`, so it was not retried:

```json
"failures": [
  {
    "url": "https://books.toscrape.com/catalogue/this-book-does-not-exist_99999/index.html",
    "stage": "fetch",
    "reason": "HTTP 404",
    "attempts": 1
  }
]
```

The committed `output/` folder is a sample from a normal run without `--fake-url`.

**Why no browser was needed:** the data is already in the HTML the server sends (toscrape.com lists Books as "Requires JavaScript ✘"). A headless browser would only add startup time, memory and cost.

## Ethics note

Scraping is a last resort. If a site offers an official API or a data export, use that. Never get around a login, a paywall, a CAPTCHA, a rate limit or a block. If a site says no, the answer is no, even when getting past it is technically easy. Collect only the fields you need, from only the pages you need, and don't collect personal data you have no reason to hold. Say who you are in the user-agent, go slowly, and cache results so the site only serves each page once.

## Honest limitations

- **The cache never expires.** Once a page is cached, the scraper keeps using that copy, so price or stock changes on the site won't show up until you delete `cache/`. That is right for development, but a real recurring job would need a maximum cache age or conditional requests (`ETag` / `If-Modified-Since`).
- Descriptions are stored exactly as the site shows them. Some of them repeat a shortened copy of the text followed by `...more`. That comes from the site's HTML, not from the parser, and it is kept on purpose so no text is made up.
- There is one simple retry with a fixed wait. The scraper does not use exponential backoff or `Retry-After`; that is planned for A16.
- The scraper runs one request at a time. That is fine for 63 pages and intentionally gentle, but it would be slow at a larger scale.

## Project layout

```
scraper/
├── src/
│   ├── config.py      # URLs, user-agent, timeout, delay: every setting in one place
│   ├── fetcher.py     # polite fetching: user-agent, timeout, delay, status check, cache, one retry
│   ├── parser.py      # extraction: HTML → the eight raw text fields
│   ├── normalize.py   # "£51.77" → 51.77, "Three" → 3, canonical URLs
│   ├── models.py      # Pydantic schema for a finished record
│   └── main.py        # entry point: runs the pipeline and writes the output and the report
├── output/            # sample output from a normal run
├── requirements.txt
└── .gitignore         # cache/, venvs, __pycache__
```
