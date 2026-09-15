"""Ticker-specific company news plus a compact dashboard digest, fetched server-side."""
from __future__ import annotations

import datetime
import email.utils
import json
import logging
import os
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
DASHBOARD_MAX_ITEMS = 40
DASHBOARD_NEWS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "dashboard-news.json")

_STOP = {"inc","inc.","corp","corp.","corporation","company","co","co.","plc","ltd","limited","sa","se","ag","nv","holdings","holding","group","the","class"}
_MARKET_QUERY = '"stock market" OR inflation OR "Federal Reserve" OR ECB OR earnings OR oil OR tariffs'
_TOPIC_KEYWORDS = {
    "rates": ("fed", "federal reserve", "ecb", "interest rate", "rates", "yield"),
    "inflation": ("inflation", "cpi", "ppi"),
    "earnings": ("earnings", "revenue", "profit", "guidance"),
    "energy": ("oil", "opec", "gas", "energy"),
    "technology": ("ai", "artificial intelligence", "semiconductor", "chip", "technology"),
    "trade": ("tariff", "trade war", "sanction"),
    "markets": ("stock market", "stocks", "wall street", "nasdaq", "s&p"),
}

def _tokens(name: str) -> list[str]:
    words=re.findall(r"[A-Za-z0-9]+", name or "")
    return [w.lower() for w in words if len(w)>=3 and w.lower() not in _STOP][:5]

def _relevant(title: str, ticker: str, name: str) -> bool:
    text=(title or "").lower()
    base=ticker.split(".")[0].lower()
    toks=_tokens(name)
    if toks and any(t in text for t in toks): return True
    if len(base)>=3 and re.search(rf"(?<![a-z0-9]){re.escape(base)}(?![a-z0-9])", text): return True
    return False

def _rss_items(query: str, limit: int = DASHBOARD_MAX_ITEMS) -> list[dict]:
    url=("https://news.google.com/rss/search?q="+urllib.parse.quote_plus(query)+"&hl=en-US&gl=US&ceid=US:en")
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
        if title and link:
            items.append({"title":title,"link":link,"published":pub,"source":source})
        if len(items)>=limit: break
    return items

def _fetch_one(ticker: str, name: str="") -> tuple[str, list[dict]]:
    base=ticker.split(".")[0]
    query=(f'"{name}" {base} stock' if name else f'"{base}" stock')
    try:
        items=[]
        for item in _rss_items(query, MAX_ITEMS_PER_TICKER * 3):
            if _relevant(item.get("title", ""), ticker, name): items.append(item)
            if len(items)>=MAX_ITEMS_PER_TICKER: break
        return ticker,items
    except Exception as e:
        log.debug("%s: news fetch failed (%s)",ticker,e)
        return ticker,[]

def _published_ts(value: str) -> float:
    try:
        dt=email.utils.parsedate_to_datetime(value or "")
        if dt.tzinfo is None: dt=dt.replace(tzinfo=datetime.timezone.utc)
        return dt.timestamp()
    except Exception:
        return 0.0

def _title_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()

def _topics(title: str) -> list[str]:
    text=(title or "").lower()
    return [topic for topic,words in _TOPIC_KEYWORDS.items() if any(word in text for word in words)][:3]

def _build_dashboard_digest(ticker_news: dict[str,list[dict]]) -> dict:
    merged={}
    for ticker,items in ticker_news.items():
        for item in items:
            key=_title_key(item.get("title", ""))
            if not key: continue
            row=merged.setdefault(key,{**item,"tickers":[],"kind":"company"})
            if ticker not in row["tickers"]: row["tickers"].append(ticker)
    try:
        market_items=_rss_items(_MARKET_QUERY, DASHBOARD_MAX_ITEMS)
    except Exception as exc:
        log.warning("dashboard news: broad market feed unavailable (%s)", exc)
        market_items=[]
    for item in market_items:
        key=_title_key(item.get("title", ""))
        if not key: continue
        row=merged.setdefault(key,{**item,"tickers":[],"kind":"market"})
        if row.get("kind") != "company": row["kind"]="market"
    now=datetime.datetime.now(datetime.timezone.utc).timestamp()
    rows=[]
    for row in merged.values():
        ts=_published_ts(row.get("published", ""))
        age_hours=max(0.0,(now-ts)/3600.0) if ts else 72.0
        topics=_topics(row.get("title", ""))
        breadth=len(row.get("tickers") or [])
        impact=(55 if row.get("kind")=="market" else 35)+min(18,breadth*6)+min(12,len(topics)*4)-min(30,age_hours*.6)
        clean={
            "title":row.get("title"),"link":row.get("link"),"published":row.get("published"),"source":row.get("source"),
            "tickers":sorted(row.get("tickers") or [])[:12],"topics":topics,"kind":row.get("kind"),"impact_score":round(max(0,min(100,impact)),1),
        }
        rows.append((impact,ts,clean))
    rows.sort(key=lambda x:(x[0],x[1]),reverse=True)
    selected=[]; market_count=0
    for _,__,row in rows:
        if row["kind"]=="market":
            if market_count>=16: continue
            market_count+=1
        selected.append(row)
        if len(selected)>=DASHBOARD_MAX_ITEMS: break
    return {
        "generated_at":datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00","Z"),
        "source":"Google News RSS",
        "note":"Compact candidate pool for the Dashboard. Client ranks portfolio intersections before display.",
        "items":selected,
    }

def _write_dashboard_digest(ticker_news: dict[str,list[dict]]) -> None:
    try:
        payload=_build_dashboard_digest(ticker_news)
        os.makedirs(os.path.dirname(DASHBOARD_NEWS_PATH),exist_ok=True)
        with open(DASHBOARD_NEWS_PATH,"w",encoding="utf-8") as fh:
            json.dump(payload,fh,separators=(",",":"),ensure_ascii=False)
        log.info("dashboard news: wrote %d compact candidates to %s",len(payload["items"]),DASHBOARD_NEWS_PATH)
    except Exception as exc:
        log.warning("dashboard news: compact digest failed (%s)",exc)

def fetch_news_for_universe(tickers: list[str], names: dict[str,str] | None=None) -> dict:
    names=names or {}
    results={}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures={pool.submit(_fetch_one,t,names.get(t,"")):t for t in tickers}
        for future in as_completed(futures):
            ticker,items=future.result()
            if items: results[ticker]=items
    log.info("news: %d/%d tickers returned relevant headlines",len(results),len(tickers))
    _write_dashboard_digest(results)
    return {"generated_at":datetime.datetime.utcnow().isoformat()+"Z","source":"Google News RSS","note":"Company-name + ticker query with relevance filtering; dossier news is asset-specific.","tickers":results}
