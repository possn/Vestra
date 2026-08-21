"""Fetch compact 1-year weekly price series for the Finscanner universe.

v0.97: the price series is now generic dossier infrastructure rather than only
an insider-chart helper. yfinance is queried in batches so the daily workflow
can attach a compact weekly history to equities and ETFs without hundreds of
serial requests. The old module name is kept to avoid breaking imports.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import math
import yfinance as yf
import requests
from urllib.parse import quote

log = logging.getLogger("insider_prices")


def _clean_close(idx, value):
    try:
        close = float(value)
    except Exception:
        return None
    if not math.isfinite(close):
        return None
    date = getattr(idx, "date", lambda: idx)()
    return {"date": str(date), "close": round(close, 6)}


def _download_batch(batch: list[str]) -> dict[str, list[dict]]:
    out = {t: [] for t in batch}
    if not batch:
        return out
    try:
        df = yf.download(
            tickers=batch,
            period="1y",
            interval="1wk",
            auto_adjust=False,
            progress=False,
            group_by="ticker",
            threads=True,
            timeout=30,
        )
        if df is None or df.empty:
            return out
        if len(batch) == 1:
            t = batch[0]
            if "Close" in df.columns:
                vals = []
                for idx, value in df["Close"].items():
                    row = _clean_close(idx, value)
                    if row:
                        vals.append(row)
                out[t] = vals[-54:]
            return out

        # group_by='ticker' normally yields columns (ticker, field).
        lvl0 = set(map(str, df.columns.get_level_values(0))) if getattr(df.columns, "nlevels", 1) > 1 else set()
        lvl1 = set(map(str, df.columns.get_level_values(1))) if getattr(df.columns, "nlevels", 1) > 1 else set()
        for t in batch:
            series = None
            try:
                if t in lvl0:
                    part = df[t]
                    if "Close" in part.columns:
                        series = part["Close"]
                elif "Close" in lvl0 and t in lvl1:
                    series = df["Close"][t]
            except Exception:
                series = None
            if series is None:
                continue
            vals = []
            for idx, value in series.items():
                row = _clean_close(idx, value)
                if row:
                    vals.append(row)
            out[t] = vals[-54:]
    except Exception as exc:
        log.warning("price history batch failed (%d tickers): %s", len(batch), exc)
    return out



def _download_direct(ticker: str) -> list[dict]:
    """Best-effort Yahoo chart fallback when yfinance batch download is empty.

    The chart endpoint is intentionally used only as a fallback. It returns the
    same public market series and does not require a user credential.
    """
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(ticker, safe='')}"
        r = requests.get(url, params={"range":"1y","interval":"1wk","events":"history","includeAdjustedClose":"true"}, headers={"User-Agent":"Mozilla/5.0 Finscanner/0.98"}, timeout=8)
        if r.status_code != 200:
            return []
        data = r.json()
        result = (((data or {}).get("chart") or {}).get("result") or [None])[0] or {}
        ts = result.get("timestamp") or []
        q = (((result.get("indicators") or {}).get("quote") or [{}])[0] or {})
        closes = q.get("close") or []
        import datetime as _dt
        out=[]
        for t,c in zip(ts, closes):
            if c is None: continue
            try:
                v=float(c)
                if not math.isfinite(v): continue
                d=_dt.datetime.utcfromtimestamp(int(t)).date().isoformat()
                out.append({"date":d,"close":round(v,6)})
            except Exception:
                continue
        return out[-54:]
    except Exception as exc:
        log.debug("direct chart fallback failed for %s: %s", ticker, exc)
        return []

def fetch_many(tickers: list[str], workers: int = 4, batch_size: int = 60) -> dict[str, list[dict]]:
    unique = sorted(set(str(t).strip() for t in tickers if t and str(t).strip()))
    out: dict[str, list[dict]] = {t: [] for t in unique}
    if not unique:
        return out
    batches = [unique[i:i+batch_size] for i in range(0, len(unique), batch_size)]
    with ThreadPoolExecutor(max_workers=max(1, min(workers, 5))) as pool:
        futures = {pool.submit(_download_batch, batch): batch for batch in batches}
        done = 0
        for fut in as_completed(futures):
            batch = futures[fut]
            try:
                out.update(fut.result())
            except Exception as exc:
                log.warning("price history batch crashed: %s", exc)
            done += len(batch)
            log.info("price histories batch phase %d/%d", min(done, len(unique)), len(unique))

    # yfinance occasionally returns an empty frame for otherwise valid tickers.
    # Recover those names individually so a transient batch failure does not
    # leave the dossier charts blank for an entire day.
    missing=[t for t in unique if len(out.get(t) or []) < 2]
    if missing:
        log.info("price histories direct fallback for %d missing tickers", len(missing))
        with ThreadPoolExecutor(max_workers=16) as pool:
            futures={pool.submit(_download_direct,t):t for t in missing}
            done=0
            for fut in as_completed(futures):
                t=futures[fut]
                try:
                    vals=fut.result()
                    if vals: out[t]=vals
                except Exception as exc:
                    log.debug("price fallback crashed for %s: %s",t,exc)
                done+=1
                if done % 50 == 0 or done == len(missing):
                    log.info("price histories fallback %d/%d",done,len(missing))
    return out
