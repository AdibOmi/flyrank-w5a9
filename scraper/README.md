# The polite scraper (FlyRank A9)

A small, polite scraping pipeline for [Books to Scrape](https://books.toscrape.com/). It reads the first 3 catalogue pages, visits all 60 book pages, and turns the HTML into validated JSON.

**Lane:** Python (Requests + Beautiful Soup + Pydantic).

> Work in progress: this README grows one stage at a time.

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
