"""Bounded prospective dividend *candidate* discovery for manual issuer review.

Yahoo Finance dividend time series often supply ex-date and amount, but not a
verifiable payment date or issuer primary-source notice. These are candidates,
NEVER verified paid dividends, and are not read by prospective return analytics.

Runs on a small rotating subset of the latest frozen Discovery cohort; network
failures remain explicitly visible. No change to portfolios, ranking or quotes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "data" / "opportunity_validation_history.json"
CANDIDATES = ROOT / "data" / "dividend_event_candidates.json"
MAX_CANDIDATES = 3000


def select_for_scan(snapshots, day, *, batch_size=12, pool_size=120):
    """Deterministic rotation; newest real cohort, highest rank first."""
    usable = [s for s in snapshots if isinstance(s, dict)
              and isinstance(s.get("observations"), dict) and s["observations"]]
    if not usable or batch_size < 1:
        return []
    latest = max(usable, key=lambda s: str(s.get("date") or ""))
    ranked = []
    for ticker, row in latest["observations"].items():
        if not isinstance(row, dict) or not str(ticker).strip():
            continue
        try:
            score = float(row["opportunity_score"])
        except (ValueError, TypeError, KeyError):
            continue
        if not math.isfinite(score):
            continue
        ranked.append((str(ticker).strip().upper(), score,
                       str(row.get("currency") or "").strip().upper()))
    ranked.sort(key=lambda x: (-x[1], x[0]))
    pool = ranked[:pool_size]
    if not pool:
        return []
    offset = ((day - dt.date(2026, 1, 1)).days * batch_size) % len(pool)
    return [pool[(offset + i) % len(pool)] for i in range(min(batch_size, len(pool)))]


def normalise_candidates(ticker, currency, series, *, checked_at):
    """Convert vendor ex-date observations to pending candidates."""
    result = []
    if series is None:
        return result
    for timestamp, raw_amount in series.items():
        try:
            ex_date = timestamp.date().isoformat()
            amount = float(raw_amount)
            if not math.isfinite(amount) or amount <= 0:
                continue
            if not checked_at - dt.timedelta(days=800) <= dt.date.fromisoformat(ex_date) <= checked_at:
                continue
        except (ValueError, TypeError, AttributeError):
            continue
        result.append({
            "ticker": ticker, "ex_date": ex_date,
            "amount_per_share": round(amount, 10),
            "currency_hint": currency or None,
            "payment_date": None,
            "status": "pending_issuer_verification",
            "source_vendor": "Yahoo Finance",
            "vendor_reference_url": "https://finance.yahoo.com/quote/"
                + quote(ticker, safe="") + "/history/?filter=div",
            "issuer_source_url": None,
            "first_seen_at": checked_at.isoformat(),
        })
    return result


def merge_candidates(previous, additions):
    """Idempotent by ticker, ex-date and amount; never auto-confirm."""
    if not isinstance(previous, dict) or not isinstance(previous.get("candidates", []), list):
        raise ValueError("Malformed dividend candidates cache")
    keyed = {}
    for item in list(previous.get("candidates", [])) + list(additions):
        if not isinstance(item, dict):
            raise ValueError("Malformed candidate record")
        key = (item.get("ticker"), item.get("ex_date"), item.get("amount_per_share"))
        if None in key:
            raise ValueError("Incomplete candidate identity")
        if item.get("status") != "pending_issuer_verification":
            raise ValueError("Candidate cache cannot contain confirmed payments")
        keyed[key] = item if key not in keyed else keyed[key]
    ordered = sorted(keyed.values(), key=lambda x:
                     (x["ex_date"], x["ticker"], x["amount_per_share"]), reverse=True)
    return ordered[:MAX_CANDIDATES]


def scan(history, previous, day, fetch_dividends, *, batch_size=12):
    targets = select_for_scan(history.get("snapshots", []), day,
                              batch_size=batch_size)
    gathered, failures = [], []
    succeeded = []
    for ticker, currency in [(t[0], t[2]) for t in targets]:
        try:
            series = fetch_dividends(ticker)
            gathered.extend(normalise_candidates(
                ticker, currency, series, checked_at=day
            ))
            succeeded.append(ticker)
        except Exception as exc:
            failures.append({"ticker": ticker,
                             "error_type": type(exc).__name__})
    candidates = merge_candidates(previous, gathered)
    collection_status = (
        "no_targets" if not targets else
        "source_unavailable" if not succeeded else
        "partial_failure" if failures else "complete"
    )
    return {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "candidates_only_unverified",
        "collection_status": collection_status,
        "successful_tickers": succeeded,
        "scanned_tickers": [t[0] for t in targets],
        "failed_tickers": failures,
        "candidates": candidates,
        "verification_note": "Vendor ex-date/amount only; issuer notice and actual payment date are missing. NEVER promote automatically to verified_dividend_events.json.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=12)
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 30:
        parser.error("batch-size must be 1..30")
    history = json.loads(HISTORY.read_text(encoding="utf-8"))
    previous = (json.loads(CANDIDATES.read_text(encoding="utf-8"))
                if CANDIDATES.exists() else {"schema_version": 1, "candidates": []})
    if previous.get("schema_version") != 1:
        raise ValueError("Unexpected dividend candidate schema")
    import yfinance as yf

    def fetch(ticker):
        # Public vendor data only. Never use vendor alone as paid-cash proof.
        return yf.Ticker(ticker).dividends

    report = scan(history, previous, dt.date.today(), fetch, batch_size=args.batch_size)
    if report["collection_status"] in {"source_unavailable", "no_targets"}:
        raise SystemExit(
            "Dividend candidate scan did not collect usable source evidence: "
            + json.dumps({
                "status": report["collection_status"],
                "scanned": report["scanned_tickers"],
                "failed": report["failed_tickers"],
            })
        )
    CANDIDATES.write_text(json.dumps(report, ensure_ascii=False, indent=2,
                                     allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"collection_status": report["collection_status"],
                      "succeeded": len(report["successful_tickers"]),
                      "scanned": len(report["scanned_tickers"]),
                      "failed": len(report["failed_tickers"]),
                      "pending_candidates": len(report["candidates"])}))


if __name__ == "__main__":
    main()
