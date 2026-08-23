"""Ticker-specific company news, fetched server-side during the daily pipeline."""
from __future__ import annotations

import datetime
import logging
import re
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

log = logging.getLogger("news")
HEADERS = {"User-Agent": "Vestra research-tool"}
MAX_ITEMS_PER_TICKER = 6
MAX_WORKERS = 12
REQUEST_TIMEOUT = 8

_STOP = {"inc","inc.","corp","corp.","corporation","company","co","co.","plc","ltd","limited","sa","se","ag","nv","holdings","holding","group","the","class"}

def _tokens(name: str) -> list[str]:
    words=re.findall(r"[A-Za-z0-9]+", name or "")
    return [w.lower() for w in words if len(w)>=3 and w.lower() not in _STOP][:5]

def _relevant(title: str, ticker: str, name: str) -> bool:
    text=(title or "").lower()
    base=ticker.split(".")[0].lower()
    toks=_tokens(name)
    # Company-name evidence is strongest. Require at least one meaningful name token.
    if toks and any(t in text for t in toks): return True
    # Ticker-only matching is allowed only for unambiguous tickers (>=3 chars),
    # and must be a standalone token to avoid M/F/O-style false positives.
    if len(base)>=3 and re.search(rf"(?<![a-z0-9]){re.escape(base)}(?![a-z0-9])", text): return True
    return False

def _fetch_one(ticker: str, name: str="") -> tuple[str, list[dict]]:
    base=ticker.split(".")[0]
    query=(f'"{name}" {base} stock' if name else f'"{base}" stock')
    url=("https://news.google.com/rss/search?q="+urllib.parse.quote_plus(query)+"&hl=en-US&gl=US&ceid=US:en")
    try:
        resp=requests.get(url,headers=HEADERS,timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        root=ET.fromstring(resp.content)
        items=[]
        for item in root.findall(".//item"):
            title=(item.findtext("title") or "").strip()
            link=(item.findtext("link") or "").strip()
            pub=(item.findtext("pubDate") or "").strip()
            source_el=item.find("source")
            source=source_el.text.strip() if source_el is not None and source_el.text else None
            if title and link and _relevant(title,ticker,name):
                items.append({"title":title,"link":link,"published":pub,"source":source})
            if len(items)>=MAX_ITEMS_PER_TICKER: break
        return ticker,items
    except Exception as e:
        log.debug("%s: news fetch failed (%s)",ticker,e)
        return ticker,[]

def fetch_news_for_universe(tickers: list[str], names: dict[str,str] | None=None) -> dict:
    names=names or {}
    results={}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures={pool.submit(_fetch_one,t,names.get(t,"")):t for t in tickers}
        for future in as_completed(futures):
            ticker,items=future.result()
            if items: results[ticker]=items
    log.info("news: %d/%d tickers returned relevant headlines",len(results),len(tickers))
    return {"generated_at":datetime.datetime.utcnow().isoformat()+"Z","source":"Google News RSS","note":"Company-name + ticker query with relevance filtering; dossier news is asset-specific.","tickers":results}
