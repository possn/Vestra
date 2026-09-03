"""Summarise timing/rate-limit markers from a Vestra pipeline log.

Read-only diagnostic helper. It does not mutate market data or participate in the
canonical build. The goal is to compare rebuilds using the same objective markers.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

_TS = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})")
_FETCH_START = re.compile(r"fundamentals: Fetching (\d+) tickers with (\d+) workers")
_FETCH_DONE = re.compile(r"fundamentals: fetched (\d+)/(\d+)")


def _ts(line: str):
    m = _TS.match(line)
    return datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S,%f") if m else None


def _seconds(start, end):
    if start is None or end is None:
        return None
    return round((end - start).total_seconds(), 3)


def summarise(text: str) -> dict:
    lines = text.splitlines()
    rate_limit_strikes = 0
    rate_limit_events = 0
    fetches = []
    active = None
    analyst_start = analyst_end = None
    insider_start = insider_end = None

    for line in lines:
        ts = _ts(line)
        if "Yahoo rate-limit detected" in line:
            rate_limit_events += 1
            m = re.search(r"strike (\d+)", line)
            if m:
                rate_limit_strikes = max(rate_limit_strikes, int(m.group(1)))

        m = _FETCH_START.search(line)
        if m:
            if active:
                fetches.append(active)
            active = {
                "tickers": int(m.group(1)),
                "workers": int(m.group(2)),
                "start": ts,
                "end": None,
            }
            continue

        m = _FETCH_DONE.search(line)
        if m and active and int(m.group(1)) == int(m.group(2)) == active["tickers"]:
            active["end"] = ts
            fetches.append(active)
            active = None

        lower = line.lower()
        if analyst_start is None and ("analyst" in lower and ("retriev" in lower or "fetch" in lower)):
            analyst_start = ts
        if "analyst" in lower and ("completed" in lower or "finished" in lower or "done" in lower):
            analyst_end = ts

        if insider_start is None and ("insider intelligence" in lower or "annotating insiders" in lower or "insider retrieval" in lower):
            insider_start = ts
        if "insider intelligence" in lower and re.search(r"\d+/\d+", line):
            m2 = re.search(r"(\d+)/(\d+)", line)
            if m2 and m2.group(1) == m2.group(2):
                insider_end = ts

    if active:
        fetches.append(active)

    fetch_summaries = []
    for row in fetches:
        fetch_summaries.append({
            "tickers": row["tickers"],
            "workers": row["workers"],
            "duration_seconds": _seconds(row["start"], row["end"]),
        })

    broad = None
    completed = [r for r in fetch_summaries if r["duration_seconds"] is not None]
    if completed:
        broad = max(completed, key=lambda r: r["tickers"])

    return {
        "rate_limit_log_events": rate_limit_events,
        "max_rate_limit_strike": rate_limit_strikes,
        "fetches": fetch_summaries,
        "broad_fetch": broad,
        "analyst_duration_seconds": _seconds(analyst_start, analyst_end),
        "insider_duration_seconds": _seconds(insider_start, insider_end),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("log", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    result = summarise(args.log.read_text(encoding="utf-8", errors="replace"))
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        args.out.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
