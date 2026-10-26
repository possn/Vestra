#!/usr/bin/env python3
"""Offline-lab source connectivity and OHLCV quality pilot. No app imports or writes."""
import csv
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

OUT=Path(os.environ.get("VESTRA_PROBE_OUTPUT","research/source_probe_result.json"))
SOURCES={
    "stooq_AAPL_US":"https://stooq.com/q/d/l/?s=aapl.us&i=d&d1=20240101&d2=20241231",
    "stooq_MSFT_US":"https://stooq.com/q/d/l/?s=msft.us&i=d&d1=20240101&d2=20241231",
    "yahoo_AAPL":"https://query1.finance.yahoo.com/v8/finance/chart/AAPL?period1=1704067200&period2=1735689600&interval=1d",
    "yahoo_MSFT":"https://query1.finance.yahoo.com/v8/finance/chart/MSFT?period1=1704067200&period2=1735689600&interval=1d",
}

def fetch(name,url):
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 VestraIndependentResearch/1.0","Accept":"text/csv,application/json"})
    try:
        with urlopen(req,timeout=18) as response:
            content=response.read(3000000).decode("utf-8")
            status=response.status
        if name.startswith("stooq"):
            rows=list(csv.DictReader(io.StringIO(content)))
            if not rows or not {"Date","Open","High","Low","Close","Volume"}.issubset(rows[0]):
                raise ValueError("missing_csv_columns_or_empty")
            dates=[r["Date"] for r in rows]
            sample=len(rows)
        else:
            payload=json.loads(content)
            chart=payload["chart"]["result"][0]
            timestamps=chart["timestamp"]
            quotes=chart["indicators"]["quote"][0]
            sample=sum(1 for i in range(len(timestamps)) if all(quotes[k][i] is not None for k in ("open","high","low","close","volume")))
            dates=[datetime.fromtimestamp(v,timezone.utc).date().isoformat() for v in timestamps]
        if len(set(dates))!=len(dates) or dates!=sorted(dates):
            raise ValueError("duplicate_or_unsorted_dates")
        return {"status":"ok","http_status":status,"rows":sample,"start_date":dates[0],"end_date":dates[-1]}
    except Exception as exc:
        return {"status":"failed","error_type":type(exc).__name__,"error":str(exc)[:220]}

def main():
    result={"purpose":"independent_historical_source_probe_only",
            "generated_at":datetime.now(timezone.utc).isoformat(),
            "no_production_changes":True,
            "research_grade_point_in_time_verified":False,
            "sources":{name:fetch(name,url) for name,url in SOURCES.items()}}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,indent=2))

if __name__=="__main__":main()
