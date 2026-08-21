"""Reliable daily FX snapshot for portfolio valuation.

Primary source: ECB euro reference rates. Yahoo Finance is used as fallback for
currencies not published by the ECB. Stored values are EUR value of 1 currency
unit, so browser-side portfolio math is simply local_value * rate_to_eur.
"""
from __future__ import annotations

import datetime as _dt
import logging
import math
import xml.etree.ElementTree as ET
from typing import Iterable

import requests
import yfinance as yf

log = logging.getLogger(__name__)
DEFAULT_CURRENCIES = ("USD", "GBP", "CHF", "CAD", "PLN", "SEK", "DKK", "AUD", "JPY", "NOK")
ECB_DAILY_XML = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"


def _ecb_rates() -> tuple[dict[str, float], str | None]:
    """Return currency->EUR value from ECB quotes (ECB publishes units per EUR)."""
    try:
        r = requests.get(ECB_DAILY_XML, timeout=20, headers={"User-Agent": "Finscanner/1.0"})
        r.raise_for_status()
        root = ET.fromstring(r.content)
        rates = {"EUR": 1.0}
        ref_date = None
        for elem in root.iter():
            if elem.tag.endswith("Cube") and elem.attrib.get("time"):
                ref_date = elem.attrib.get("time")
            c = elem.attrib.get("currency")
            raw = elem.attrib.get("rate")
            if c and raw:
                q = float(raw)
                if q > 0 and math.isfinite(q):
                    rates[c.upper()] = 1.0 / q
        return rates, ref_date
    except Exception as exc:
        log.warning("ECB FX fetch failed: %s", exc)
        return {"EUR": 1.0}, None


def _last_close(symbol: str) -> float | None:
    try:
        hist = yf.Ticker(symbol).history(period="5d", interval="1d", auto_adjust=False)
        if hist is None or hist.empty or "Close" not in hist:
            return None
        vals = [float(v) for v in hist["Close"].dropna().tolist() if math.isfinite(float(v))]
        return vals[-1] if vals else None
    except Exception as exc:
        log.warning("FX fetch failed for %s: %s", symbol, exc)
        return None


def _yahoo_to_eur(currency: str) -> tuple[float | None, str | None]:
    c = currency.upper()
    if c == "EUR":
        return 1.0, "identity"
    direct = _last_close(f"{c}EUR=X")
    if direct and direct > 0:
        return direct, f"{c}EUR=X"
    inverse = _last_close(f"EUR{c}=X")
    if inverse and inverse > 0:
        return 1.0 / inverse, f"EUR{c}=X (inverted)"
    return None, None


def build_fx_payload(currencies: Iterable[str] = DEFAULT_CURRENCIES, previous: dict | None = None) -> dict:
    requested = [str(c).upper() for c in currencies]
    ecb, ecb_date = _ecb_rates()
    rates = {"EUR": 1.0}
    sources = {"EUR": "identity"}
    stale = []
    previous_rates = (previous or {}).get("rates_to_eur") or {}

    for c in requested:
        if c == "EUR":
            continue
        if c in ecb and ecb[c] > 0:
            rates[c] = ecb[c]
            sources[c] = f"ECB {ecb_date or 'latest'}"
            continue
        rate, source = _yahoo_to_eur(c)
        if rate is not None:
            rates[c] = rate
            sources[c] = source or "Yahoo Finance"
            continue
        old = previous_rates.get(c)
        if old is not None and float(old) > 0:
            rates[c] = float(old)
            sources[c] = "previous snapshot fallback"
            stale.append(c)

    missing = [c for c in requested if c != "EUR" and c not in rates]
    return {
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "base": "EUR",
        "rates_to_eur": rates,
        "sources": sources,
        "ecb_reference_date": ecb_date,
        "missing": missing,
        "stale_fallback": stale,
        "note": "rate = EUR value of 1 currency unit; GBp/GBX are handled browser-side as 1/100 GBP",
    }
