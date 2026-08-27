#!/usr/bin/env python3
"""Build a lightweight metals-news snapshot for Vestra.

Uses public Google News RSS search results as discovery headlines only. The app
links to the original destination and never republishes article bodies.
"""
from __future__ import annotations

import email.utils
import json
import pathlib
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "metals-news.json"

QUERIES = {
    "gold": 'gold commodity OR gold price when:7d',
    "silver": 'silver commodity OR silver price when:7d',
    "copper": 'copper commodity OR copper price when:7d',
    "platinum": 'platinum commodity OR platinum price when:7d',
    "palladium": 'palladium commodity OR palladium price when:7d',
    "uranium": 'uranium commodity OR uranium price when:14d',
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 Vestra/1.0 (+https://possn.github.io)",
    "Accept": "application/rss+xml,application/xml,text/xml;q=0.9,*/*;q=0.8",
}


def iso_date(value: str) -> str:
    try:
        dt = email.utils.parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception:
        return ""


def fetch_feed(metal: str, query: str) -> list[dict]:
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({
        "q": query,
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en",
    })
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        root = ET.fromstring(resp.read())
    rows: list[dict] = []
    for item in root.findall("./channel/item")[:8]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        source_node = item.find("source")
        source = ((source_node.text or "").strip() if source_node is not None else "")
        published = iso_date((item.findtext("pubDate") or "").strip())
        if not title or not link:
            continue
        rows.append({
            "metal": metal,
            "title": title,
            "url": link,
            "source": source or "Google News",
            "published_at": published,
        })
    return rows


def previous_snapshot() -> dict | None:
    if not OUT.exists():
        return None
    try:
        data = json.loads(OUT.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("items"), list) and data["items"]:
            return data
    except Exception:
        pass
    return None


def main() -> None:
    items: list[dict] = []
    failures: list[str] = []
    seen: set[tuple[str, str]] = set()
    for metal, query in QUERIES.items():
        try:
            rows = fetch_feed(metal, query)
        except Exception as exc:
            failures.append(f"{metal}: {exc}")
            continue
        kept = 0
        for row in rows:
            key = (metal, row["title"].casefold())
            if key in seen:
                continue
            seen.add(key)
            items.append(row)
            kept += 1
            if kept >= 4:
                break

    if not items:
        old = previous_snapshot()
        if old:
            print("All feeds failed; preserving prior non-empty metals snapshot")
            return
        raise SystemExit("No metals news could be retrieved and no prior snapshot exists")

    items.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "Google News RSS discovery",
        "coverage": list(QUERIES),
        "partial": bool(failures),
        "failures": failures,
        "items": items,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"metals news: {len(items)} headlines; failures={len(failures)}")


if __name__ == "__main__":
    main()
