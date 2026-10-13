#!/usr/bin/env python3
"""Fetch the actual CNN Business Fear & Greed Index; never substitute the Vestra score."""
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
OUTPUT = Path(__file__).resolve().parents[1] / "data/cnn-fear-greed.json"
FIELDS = ("score", "previous_close", "previous_1_week", "previous_1_month", "previous_1_year")

def normalized(raw):
    item = raw.get("fear_and_greed") or {}
    score = item.get("score")
    if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 100:
        raise ValueError("CNN score missing or invalid")
    values = {"source": "cnn", "score": score, "rating": str(item.get("rating") or ""), "timestamp": str(item.get("timestamp") or "")}
    for field in FIELDS[1:]:
        n = item.get(field)
        values[field] = n if isinstance(n, (int, float)) and not isinstance(n, bool) and math.isfinite(n) and 0 <= n <= 100 else None
    if not values["timestamp"]:
        raise ValueError("CNN timestamp missing")
    dt = datetime.fromisoformat(values["timestamp"].replace("Z", "+00:00"))
    if dt.tzinfo is None or abs((datetime.now(timezone.utc)-dt.astimezone(timezone.utc)).total_seconds()) > 86400 * 10:
        raise ValueError("CNN data stale or timestamp invalid")
    return values

def main():
    request = Request(URL, headers={
        "User-Agent": os.getenv("CNN_FETCH_USER_AGENT", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"),
        "Referer": "https://www.cnn.com/markets/fear-and-greed",
        "Accept": "application/json",
    })
    with urlopen(request, timeout=18) as response:
        payload = json.load(response)
    data = normalized(payload)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"status": "updated", "score": data["score"], "timestamp": data["timestamp"]}))

if __name__ == "__main__":
    main()
