"""
news.py — headlines per ticker, fetched server-side during the pipeline.

WHY SERVER-SIDE: the previous approach tried to fetch news directly from
the browser (client-side fetch() to Yahoo's search endpoint). That is
fundamentally broken, not just flaky — CORS is enforced by the browser,
and Yahoo's endpoints don't send the Access-Control-Allow-Origin header
that would permit a cross-origin browser request to succeed. No amount
of retrying or reformatting fixes that; the fetch must happen somewhere
CORS doesn't apply, i.e. server-side. Confirmed via real user testing:
every single ticker (including AAPL) failed identically in-browser.

SOURCE: Google News RSS search (`news.google.com/rss/search`). No API
key, no auth, generous with automated requests, and reliably returns
real, dated headlines with working links. This is a genuine trade-off
versus a real financial news API (Benzinga, Polygon, etc.) which would
need a paid key — RSS is the free option.

SCOPE: every ticker in the tracked universe (not just portfolio/watchlist
— those live in the browser's localStorage and the pipeline has no way
to know what a given user holds). A ticker outside the tracked universe
still won't have pre-fetched news, same limitation as score/sector data.
"""
from __future__ import annotations

import datetime
import logging
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

log = logging.getLogger("news")

HEADERS = {"User-Agent": "Finscanner research-tool finscanner-app@proton.me"}
MAX_ITEMS_PER_TICKER = 4
MAX_WORKERS = 15
REQUEST_TIMEOUT = 8


def _fetch_one(ticker: str) -> tuple[str, list[dict]]:
    # Strip exchange suffix for the query — "AIR.PA" searches better as
    # "AIR stock" than "AIR.PA stock" against a general news index.
    query_ticker = ticker.split(".")[0]
    url = (
        "https://news.google.com/rss/search"
        f"?q={query_ticker}+stock&hl=en-US&gl=US&ceid=US:en"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        items = []
        for item in root.findall(".//item")[:MAX_ITEMS_PER_TICKER]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            source_el = item.find("source")
            source = source_el.text.strip() if source_el is not None and source_el.text else None
            if title and link:
                items.append({"title": title, "link": link, "published": pub_date, "source": source})
        return ticker, items
    except Exception as e:
        log.debug("%s: news fetch failed (%s)", ticker, e)
        return ticker, []


def fetch_news_for_universe(tickers: list[str]) -> dict:
    results: dict[str, list[dict]] = {}
    done = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_fetch_one, t): t for t in tickers}
        for future in as_completed(futures):
            ticker, items = future.result()
            if items:  # skip empty entries — smaller file, and "ticker not
                results[ticker] = items  # in dict" already means "no news" to the frontend
            done += 1
            if done % 200 == 0:
                log.info("news fetch %d/%d", done, len(tickers))

    log.info("news: %d/%d tickers returned at least one headline", len(results), len(tickers))
    return {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "source": "Google News RSS (news.google.com/rss/search)",
        "note": (
            "Fetched server-side during the daily pipeline run — client-side "
            "fetching from the browser is blocked by CORS on essentially every "
            "financial news source, including Yahoo Finance. Coverage is "
            "limited to tickers in the tracked universe."
        ),
        "tickers": results,
    }
