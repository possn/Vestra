from __future__ import annotations

import datetime as dt
import io
import json
import re
from pathlib import Path

import pdfplumber
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "executives.json"

# Official public filings. Discovery of new filings can be extended without
# changing the JSON/UI contract; every configured document is downloaded fresh.
FILINGS = [
    {
        "url": "https://www.whitehouse.gov/wp-content/uploads/2026/06/President-Donald-J.-Trump-Periodic-Transaction-Report-0.6.25.26-2.pdf",
        "disclosure_date": "2026-06-25",
        "source": "White House / OGE Form 278-T",
    },
    {
        "url": "https://extapps2.oge.gov/201/Presiden.nsf/PAS%2BIndex/405E4EC4E27BE8D185258DF7002DD1C0/%24FILE/Trump%2C%20Donald%20J.-05.08.2026-278T%282%29.pdf",
        "disclosure_date": "2026-05-08",
        "source": "U.S. Office of Government Ethics / OGE Form 278-T",
    },
]

# Only publish mappings that are unambiguous in the filing text. This is
# intentionally conservative: an unknown asset is omitted rather than guessed.
ASSET_TICKERS = {
    "NVIDIA": "NVDA",
    "BOEING": "BA",
    "VANGUARD S&P 500": "VOO",
    "COMCAST": "CMCSA",
    "PTC INC": "PTC",
    "ACCENTURE": "ACN",
    "ADVANCED MICRO DEVICES": "AMD",
    "ENERGY SELECT SECTOR SPDR": "XLE",
    "EQUINIX": "EQIX",
    "DIGITAL REALTY": "DLR",
    "MICROSOFT": "MSFT",
    "AMAZON": "AMZN",
    "META PLATFORMS": "META",
    "FACEBOOK": "META",
    "VANGUARD DIVIDEND APPRECIATION": "VIG",
    "WALT DISNEY": "DIS",
    "DISNEY": "DIS",
    "UNITEDHEALTH": "UNH",
    "ORACLE": "ORCL",
    "CDW": "CDW",
    "NETFLIX": "NFLX",
    "PALO ALTO NETWORKS": "PANW",
    "INTEL": "INTC",
    "ALPHABET": "GOOGL",
    "GOOGLE": "GOOGL",
    "APPLE": "AAPL",
    "BROADCOM": "AVGO",
    "TESLA": "TSLA",
    "SALESFORCE": "CRM",
    "ADOBE": "ADBE",
    "COSTCO": "COST",
    "JPMORGAN": "JPM",
    "BANK OF AMERICA": "BAC",
    "GOLDMAN SACHS": "GS",
    "MORGAN STANLEY": "MS",
    "BLACKROCK": "BLK",
    "VISA": "V",
    "MASTERCARD": "MA",
    "COCA-COLA": "KO",
    "COCA COLA": "KO",
    "PEPSICO": "PEP",
    "WALMART": "WMT",
    "HOME DEPOT": "HD",
    "CATERPILLAR": "CAT",
    "LOCKHEED MARTIN": "LMT",
    "RTX": "RTX",
    "RAYTHEON": "RTX",
    "EXXON": "XOM",
    "CHEVRON": "CVX",
}

AMOUNT_RE = re.compile(r"\$\s*([0-9,]+)\s*(?:-|–|—|to)\s*\$?\s*([0-9,]+)", re.I)
DATE_RE = re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b")
TYPE_RE = re.compile(r"\b(purchase|sale|exchange)\b", re.I)


def normalise_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def iso_date(value: str) -> str:
    value = (value or "").strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return dt.datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    return ""


def ticker_for(description: str) -> str:
    upper = normalise_space(description).upper()
    for needle, ticker in sorted(ASSET_TICKERS.items(), key=lambda kv: len(kv[0]), reverse=True):
        if needle in upper:
            return ticker
    return ""


def parse_row_text(text: str, filing: dict) -> dict | None:
    line = normalise_space(text)
    typ = TYPE_RE.search(line)
    amount = AMOUNT_RE.search(line)
    dates = DATE_RE.findall(line)
    if not typ or not amount or not dates:
        return None
    ticker = ticker_for(line)
    if not ticker:
        return None
    transaction_date = iso_date(dates[-1])
    if not transaction_date:
        return None
    lo, hi = amount.groups()
    trade_type = {"purchase": "buy", "sale": "sell", "exchange": "exchange"}[typ.group(1).lower()]
    return {
        "ticker": ticker,
        "member": "Donald J. Trump",
        "member_key": "executive:donald-trump",
        "chamber": "Executive",
        "type": trade_type,
        "amount": f"${lo} - ${hi}",
        "transaction_date": transaction_date,
        "disclosure_date": filing["disclosure_date"],
        "asset": line[:500],
        "filing_url": filing["url"],
        "source": filing["source"],
    }


def extract_pdf_rows(content: bytes, filing: dict) -> list[dict]:
    trades: list[dict] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
            # First try individual OCR/text lines.
            for line in text.splitlines():
                row = parse_row_text(line, filing)
                if row:
                    trades.append(row)
            # Some 278-T PDFs split table cells onto separate text lines. Tables
            # are a slower fallback, but substantially improve robustness.
            if not trades or len(trades) < 10:
                try:
                    for table in page.extract_tables() or []:
                        for cells in table or []:
                            row = parse_row_text(" ".join(normalise_space(x or "") for x in cells), filing)
                            if row:
                                trades.append(row)
                except Exception:
                    pass
    return trades


def trade_key(row: dict) -> tuple:
    return (
        row.get("ticker"), row.get("type"), row.get("amount"),
        row.get("transaction_date"), row.get("member"),
    )


def existing_payload() -> dict:
    try:
        value = json.loads(OUT.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def main() -> None:
    old = existing_payload()
    rows: list[dict] = []
    filing_status = []
    session = requests.Session()
    session.headers.update({"User-Agent": "Vestra/1.0 public-financial-disclosure research"})

    for filing in FILINGS:
        try:
            response = session.get(filing["url"], timeout=90)
            response.raise_for_status()
            parsed = extract_pdf_rows(response.content, filing)
            rows.extend(parsed)
            filing_status.append({"url": filing["url"], "disclosure_date": filing["disclosure_date"], "parsed_trades": len(parsed), "ok": True})
        except Exception as exc:
            filing_status.append({"url": filing["url"], "disclosure_date": filing["disclosure_date"], "parsed_trades": 0, "ok": False, "error": str(exc)[:180]})

    merged = {}
    # Preserve previously verified rows; newly parsed official rows overwrite an
    # identical transaction so their newest source metadata wins.
    for row in old.get("trades") or []:
        if isinstance(row, dict) and row.get("ticker"):
            merged[trade_key(row)] = row
    for row in rows:
        merged[trade_key(row)] = row
    trades = list(merged.values())
    trades.sort(key=lambda x: (x.get("disclosure_date") or "", x.get("transaction_date") or "", x.get("ticker") or ""), reverse=True)

    buys = sum(1 for x in trades if x.get("type") == "buy")
    sells = sum(1 for x in trades if x.get("type") == "sell")
    if len(trades) < 20 or buys < 10 or sells < 10:
        if old.get("trades"):
            print(f"Executive parser coverage insufficient ({len(trades)} trades, {buys} buys, {sells} sells); preserving previous valid snapshot")
            return
        raise SystemExit("Executive parser did not reach minimum safe coverage")

    newest = max((x.get("disclosure_date") or "" for x in trades), default="")
    out = {
        "schema_version": 2,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": "White House + U.S. Office of Government Ethics",
        "source_origin": "Official Executive Branch OGE Form 278-T disclosures",
        "coverage": "automated_official_oge",
        "newest_disclosure": newest,
        "people": [{
            "key": "executive:donald-trump",
            "name": "Donald J. Trump",
            "role": "President of the United States",
            "chamber": "Executive",
            "source_label": "OGE Form 278-T",
            "source_url": FILINGS[0]["url"],
            "count": len(trades),
            "buys": buys,
            "sells": sells,
            "last": newest,
        }],
        "trades": trades,
        "filings": filing_status,
        "note": "Executive disclosures are separate from congressional STOCK Act data. Only transactions whose listed asset can be mapped unambiguously to a market ticker are published by Vestra.",
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Executive feed: {len(trades)} mapped trades ({buys} buys / {sells} sells), newest {newest}")


if __name__ == "__main__":
    main()
