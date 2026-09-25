"""Entry point for the polite scraper. Run from the scraper/ folder:  python -m src.main

Stage 0: target classified (see README). No requests are made yet.
"""

TARGET = "https://books.toscrape.com/"
MAX_CATALOGUE_PAGES = 3


def main() -> None:
    print(f"target={TARGET} scope=first {MAX_CATALOGUE_PAGES} catalogue pages")
    print("robots.txt: HTTP 404 (no robots file found); permission comes from the sandbox statement")


if __name__ == "__main__":
    main()
