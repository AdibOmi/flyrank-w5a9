"""All tunable settings in one place."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache"
OUTPUT_DIR = ROOT / "output"

START_URL = "https://books.toscrape.com/catalogue/page-1.html"
MAX_CATALOGUE_PAGES = 3
ALLOWED_HOST = "books.toscrape.com"

# Honest identity: a site owner reading their logs can find out who we are.
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/AdibOmi/flyrank-w5a9)"

TIMEOUT_SECONDS = 10       # never wait forever
DELAY_SECONDS = 1.0        # min gap between real requests (assignment floor is 0.5 s)
RETRY_WAIT_SECONDS = 2.0   # one retry, only for timeouts / connection errors / 5xx

# Deliberately fake book URL used to prove one bad page cannot kill the run.
FAKE_BOOK_URL = "https://books.toscrape.com/catalogue/this-book-does-not-exist_99999/index.html"
