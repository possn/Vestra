#!/usr/bin/env python3
"""Read-only provider connectivity smoke test; no market observations are stored.

This is NOT an empirical research dataset. Never print bearer keys or HTTP URLs
containing credentials. EODHD demo covers a tiny survivor-selected universe.
"""
from __future__ import annotations
import argparse
import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

SUPPORTED = {"eodhd": "https://eodhd.com/api/eod/"}
DEMO_SYMBOLS = frozenset(("AAPL.US", "TSLA.US", "AMZN.US", "VTI.US"))


def probe_eodhd(*, token=None, symbol="AAPL.US", transport=None):
    """Return non-sensitive diagnostics, never data or credentials."""
    key = token or os.environ.get("EODHD_API_TOKEN")
    if not key:
        return {"status":"BLOCKED_DATA_ACCESS","reason":"EODHD_API_TOKEN_not_configured",
                "empirical_validated":False}
    if key == "demo" and symbol not in DEMO_SYMBOLS:
        return {"status":"BLOCKED_DEMO_SCOPE","empirical_validated":False}
    query = urlencode({"api_token":key,"fmt":"json","from":"2020-01-01",
                       "to":"2020-01-10","order":"a"})
    request = Request(SUPPORTED["eodhd"] + symbol + "?" + query,
                      headers={"User-Agent":"VestraResearchProbe/1.0"})
    try:
        if transport is None:
            transport = urlopen
        with transport(request, timeout=12) as response:
            payload = response.read(2_000_001)
            if len(payload)>2_000_000:
                return {"status":"REJECTED_PROVIDER_RESPONSE","reason":"oversized",
                        "empirical_validated":False}
            data = json.loads(payload)
    except (HTTPError, URLError, OSError, TimeoutError, ValueError, TypeError):
        return {"status":"PROVIDER_UNAVAILABLE_OR_NOT_ENTITLED","empirical_validated":False}
    if not isinstance(data,list) or not data:
        return {"status":"REJECTED_PROVIDER_RESPONSE","reason":"empty_or_invalid",
                "empirical_validated":False}
    dates=[r.get("date") for r in data if isinstance(r,dict)]
    if len(dates)!=len(data) or not all(isinstance(x,str) and len(x)==10 for x in dates):
        return {"status":"REJECTED_PROVIDER_RESPONSE","reason":"invalid_dates",
                "empirical_validated":False}
    return {"status":"DEMO_CONNECTIVITY_ONLY" if key=="demo" else "PROVIDER_ACCESS_DETECTED_NOT_PIT_AUDITED",
            "provider":"eodhd","symbol":symbol,"bars":len(data),
            "first_session":min(dates),"last_session":max(dates),
            "empirical_validated":False,
            "limitations":["no_authentication_of_vendor_history","no_delistings_asof_universe",
                           "no_corporate_action_or_calendar_audit","not_alpha_evidence"]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol",default="AAPL.US")
    parser.add_argument("--demo",action="store_true",
                        help="Use public demo key; tiny nonrepresentative scope")
    args=parser.parse_args()
    result=probe_eodhd(token="demo" if args.demo else None,symbol=args.symbol)
    print(json.dumps(result,sort_keys=True))
    return 0 if result["status"] in ("DEMO_CONNECTIVITY_ONLY",
                                     "PROVIDER_ACCESS_DETECTED_NOT_PIT_AUDITED") else 2

if __name__=="__main__":
    raise SystemExit(main())
