#!/usr/bin/env python3
import json
import re
from datetime import datetime, timezone, date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://www.aaii.com/sentimentsurvey/sent_results?adv=yes"
OUT = Path("data/aaii-sentiment.json")
DATE_RE = re.compile(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})$")


def infer_year(month: int, now: datetime) -> int:
    year = now.year
    if month > now.month + 3:
        year -= 1
    return year


def parse_rows(html: str, now: datetime | None = None):
    now = now or datetime.now(timezone.utc)
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for tr in soup.find_all("tr"):
        cells = [" ".join(td.get_text(" ", strip=True).split()) for td in tr.find_all(["td", "th"])]
        if len(cells) < 4:
            continue
        m = DATE_RE.match(cells[0])
        if not m:
            continue
        try:
            month = datetime.strptime(m.group(1), "%b").month
            day = int(m.group(2))
            year = infer_year(month, now)
            date = datetime(year, month, day, tzinfo=timezone.utc).date().isoformat()
            bullish = float(cells[1].rstrip("%"))
            neutral = float(cells[2].rstrip("%"))
            bearish = float(cells[3].rstrip("%"))
        except (ValueError, TypeError):
            continue
        rows.append({"date": date, "bullish": bullish, "neutral": neutral, "bearish": bearish})

    deduped = {row["date"]: row for row in rows}
    return sorted(deduped.values(), key=lambda row: row["date"], reverse=True)


def main():
    response = requests.get(
        URL,
        timeout=25,
        headers={"User-Agent": "Vestra/1.0 (+https://github.com/possn/Vestra)", "Cache-Control": "no-cache"},
    )
    response.raise_for_status()
    weeks = parse_rows(response.text)[:5]
    if len(weeks) < 5:
        raise RuntimeError(f"Expected at least 5 AAII weekly rows, found {len(weeks)}")

    # Never publish a historical/cached AAII page as a current survey.
    # AAII reports once per week; allow the full weekly publication window.
    age = (datetime.now(timezone.utc).date() - date.fromisoformat(weeks[0]["date"])).days
    if not 0 <= age <= 8:
        raise RuntimeError(f"AAII historical source stale: latest week {weeks[0]['date']} ({age} days old)")

    for row in weeks:
        total = row["bullish"] + row["neutral"] + row["bearish"]
        if not 99.0 <= total <= 101.0:
            raise RuntimeError(f"Invalid AAII percentages for {row['date']}: total={total:.1f}")

    payload = {
        "source": "AAII Investor Sentiment Survey",
        "source_url": URL,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "latest_published": weeks[0]["date"],
        "weeks": weeks,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(weeks)} AAII weeks, latest {weeks[0]['date']}")


if __name__ == "__main__":
    main()
