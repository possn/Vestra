"""Historical ECB FX series for transaction-date portfolio cost basis.

Stores EUR value of one unit of each currency as compact per-currency series.
ECB reference rates are quoted as currency units per EUR, so we invert them.
"""
from __future__ import annotations

import datetime as dt
import logging
import math
import xml.etree.ElementTree as ET
from typing import Iterable

import requests

log = logging.getLogger(__name__)
ECB_HIST_XML = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml"
DEFAULT_CURRENCIES = ("USD", "GBP", "CHF", "CAD", "PLN", "SEK", "DKK", "AUD", "JPY", "NOK")


def build_fx_history_payload(currencies: Iterable[str] = DEFAULT_CURRENCIES, previous: dict | None = None) -> dict:
    wanted = {str(c).upper() for c in currencies if str(c).strip()}
    wanted.add("EUR")
    series: dict[str, list[list[object]]] = {c: [] for c in wanted}
    # EUR is identity for every date; browser handles it without series entries.
    try:
        r = requests.get(ECB_HIST_XML, timeout=30, headers={"User-Agent": "Finscanner/1.0"})
        r.raise_for_status()
        root = ET.fromstring(r.content)
        min_date = None
        max_date = None
        for day in root.iter():
            date = day.attrib.get("time")
            if not date:
                continue
            min_date = date if min_date is None or date < min_date else min_date
            max_date = date if max_date is None or date > max_date else max_date
            for elem in day:
                c = str(elem.attrib.get("currency") or "").upper()
                raw = elem.attrib.get("rate")
                if c not in wanted or not raw:
                    continue
                try:
                    quote = float(raw)
                except (TypeError, ValueError):
                    continue
                if quote > 0 and math.isfinite(quote):
                    series[c].append([date, 1.0 / quote])
        series = {c: vals for c, vals in series.items() if vals}
        return {
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "base": "EUR",
            "source": "ECB eurofxref historical reference rates",
            "date_min": min_date,
            "date_max": max_date,
            "series": series,
            "note": "Each point is [date, EUR value of 1 currency unit]. Browser uses the latest reference rate on or before the transaction date. EUR=1; GBp/GBX are 1/100 GBP.",
        }
    except Exception as exc:
        log.warning("ECB historical FX fetch failed: %s", exc)
        if previous and isinstance(previous.get("series"), dict) and previous.get("series"):
            out = dict(previous)
            out["generated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
            out["stale_fallback"] = True
            out["last_error"] = str(exc)
            return out
        return {
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "base": "EUR",
            "source": "ECB eurofxref historical reference rates",
            "series": {},
            "stale_fallback": False,
            "last_error": str(exc),
        }
