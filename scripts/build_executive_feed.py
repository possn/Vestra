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

ASSET_TICKERS = {
    "NVIDIA": "NVDA", "BOEING": "BA", "VANGUARD S&P 500": "VOO", "COMCAST": "CMCSA",
    "PTC INC": "PTC", "ACCENTURE": "ACN", "ADVANCED MICRO DEVICES": "AMD",
    "ENERGY SELECT SECTOR SPDR": "XLE", "EQUINIX": "EQIX", "DIGITAL REALTY": "DLR",
    "MICROSOFT": "MSFT", "AMAZON": "AMZN", "META PLATFORMS": "META", "FACEBOOK": "META",
    "VANGUARD DIVIDEND APPRECIATION": "VIG", "WALT DISNEY": "DIS", "DISNEY": "DIS",
    "UNITEDHEALTH": "UNH", "ORACLE": "ORCL", "CDW": "CDW", "NETFLIX": "NFLX",
    "PALO ALTO NETWORKS": "PANW", "INTEL": "INTC", "ALPHABET": "GOOGL", "GOOGLE": "GOOGL",
    "APPLE": "AAPL", "BROADCOM": "AVGO", "TESLA": "TSLA", "SALESFORCE": "CRM",
    "ADOBE": "ADBE", "COSTCO": "COST", "JPMORGAN": "JPM", "BANK OF AMERICA": "BAC",
    "GOLDMAN SACHS": "GS", "MORGAN STANLEY": "MS", "BLACKROCK": "BLK", "VISA": "V",
    "MASTERCARD": "MA", "COCA-COLA": "KO", "COCA COLA": "KO", "PEPSICO": "PEP",
    "WALMART": "WMT", "HOME DEPOT": "HD", "CATERPILLAR": "CAT", "LOCKHEED MARTIN": "LMT",
    "RTX": "RTX", "RAYTHEON": "RTX", "EXXON": "XOM", "CHEVRON": "CVX",
    "ILLINOIS TOOL WKS": "ITW", "ILLINOIS TOOL WORKS": "ITW", "MCDONALDS CORP": "MCD",
    "MCDONALD'S": "MCD", "MCDONALDS": "MCD", "MEDTRONIC": "MDT",
    "STATE STREET SPDR S&P DIVIDEND ETF": "SDY", "SPDR S&P DIVIDEND ETF": "SDY",
}

AMOUNT_RE = re.compile(r"\$\s*([0-9][0-9,.]*)\s*(?:-|–|—|to|•)\s*\$?\s*([0-9][0-9,.]*)", re.I)
OCR_AMOUNT_RE = re.compile(r"\$?\s*([0-9][0-9,.]{2,})\s*(?:-|–|—|to|•)\s*\$?\s*([0-9][0-9,.]{2,})", re.I)
DATE_RE = re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b")
TYPE_RE = re.compile(r"\b(purchase|sale|exchange)\b", re.I)
LOGICAL_ROW_RE = re.compile(
    r"(?:^|\s)\d{1,5}\s+(?P<asset>.{2,220}?)\s+(?P<type>purchase|sale|exchange)\s+"
    r"(?P<date>\d{1,2}/\d{1,2}/\d{2,4})\s+(?:Yes|No)\s+"
    r"\$\s*(?P<lo>[0-9][0-9,.]*)\s*(?:-|–|—|to|•)\s*\$?\s*(?P<hi>[0-9][0-9,.]*)",
    re.I,
)


def normalise_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def money_digits(value: str) -> str:
    return re.sub(r"[^0-9]", "", value or "")


def iso_date(value: str) -> str:
    value = (value or "").strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return dt.datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    return ""


def ticker_matches(description: str) -> list[str]:
    upper = normalise_space(description).upper()
    found = []
    for needle, ticker in sorted(ASSET_TICKERS.items(), key=lambda kv: len(kv[0]), reverse=True):
        if needle in upper and ticker not in found:
            found.append(ticker)
    return found


def ticker_for(description: str) -> str:
    found = ticker_matches(description)
    return found[0] if len(found) == 1 else ""


def make_trade(*, ticker: str, trade_type: str, amount: str, transaction_date: str, asset: str, filing: dict) -> dict:
    return {
        "ticker": ticker,
        "member": "Donald J. Trump",
        "member_key": "executive:donald-trump",
        "chamber": "Executive",
        "type": trade_type,
        "amount": amount,
        "transaction_date": transaction_date,
        "disclosure_date": filing["disclosure_date"],
        "asset": normalise_space(asset)[:500],
        "filing_url": filing["url"],
        "source": filing["source"],
    }


def parse_candidate(text: str, filing: dict, *, amount_re=AMOUNT_RE) -> dict | None:
    line = normalise_space(text)
    types = TYPE_RE.findall(line)
    amounts = list(amount_re.finditer(line))
    dates = DATE_RE.findall(line)
    if len(types) != 1 or len(amounts) != 1 or len(dates) != 1:
        return None
    ticker = ticker_for(line)
    if not ticker:
        return None
    transaction_date = iso_date(dates[0])
    if not transaction_date:
        return None
    lo, hi = money_digits(amounts[0].group(1)), money_digits(amounts[0].group(2))
    if not lo or not hi:
        return None
    lo_i, hi_i = int(lo), int(hi)
    if lo_i <= 0 or hi_i < lo_i:
        return None
    trade_type = {"purchase": "buy", "sale": "sell", "exchange": "exchange"}[types[0].lower()]
    return make_trade(
        ticker=ticker, trade_type=trade_type, amount=f"${lo_i:,} - ${hi_i:,}",
        transaction_date=transaction_date, asset=line, filing=filing,
    )


def parse_row_text(text: str, filing: dict) -> dict | None:
    return parse_candidate(text, filing, amount_re=AMOUNT_RE)


def parse_logical_rows(text: str, filing: dict) -> list[dict]:
    flat = normalise_space(text)
    out = []
    for match in LOGICAL_ROW_RE.finditer(flat):
        asset = normalise_space(match.group("asset"))
        ticker = ticker_for(asset)
        transaction_date = iso_date(match.group("date"))
        if not ticker or not transaction_date:
            continue
        lo, hi = money_digits(match.group("lo")), money_digits(match.group("hi"))
        if not lo or not hi or int(hi) < int(lo):
            continue
        trade_type = {"purchase": "buy", "sale": "sell", "exchange": "exchange"}[match.group("type").lower()]
        out.append(make_trade(
            ticker=ticker, trade_type=trade_type, amount=f"${int(lo):,} - ${int(hi):,}",
            transaction_date=transaction_date, asset=asset, filing=filing,
        ))
    return out


def parse_text_blob(text: str, filing: dict) -> list[dict]:
    rows = parse_logical_rows(text, filing)
    for line in text.splitlines():
        row = parse_row_text(line, filing)
        if row:
            rows.append(row)
    return rows


def parse_ocr_windows(text: str, filing: dict) -> list[dict]:
    """Recover scanned table rows that Tesseract splits across adjacent lines.

    A candidate is accepted only if one 1-4-line window contains exactly one
    recognised asset, one transaction type, one date and one plausible amount
    range. This keeps OCR fallback conservative while tolerating column wrapping.
    """
    lines = [normalise_space(x) for x in (text or "").splitlines() if normalise_space(x)]
    rows: list[dict] = []
    for i in range(len(lines)):
        for width in range(1, 5):
            chunk = " ".join(lines[i:i + width])
            if not TYPE_RE.search(chunk) or not DATE_RE.search(chunk) or not ticker_for(chunk):
                continue
            row = parse_candidate(chunk, filing, amount_re=OCR_AMOUNT_RE)
            if row:
                rows.append(row)
                break
    return rows


def ocr_page_text(page) -> str:
    try:
        import pytesseract
    except Exception:
        return ""
    try:
        image = page.to_image(resolution=165, antialias=True).original.convert("L")
        return pytesseract.image_to_string(image, config="--psm 6") or ""
    except Exception as exc:
        print(f"OCR page failed: {exc}")
        return ""


def trade_key(row: dict) -> tuple:
    return (
        row.get("ticker"), row.get("type"), row.get("amount"), row.get("transaction_date"),
        row.get("member"), row.get("disclosure_date"),
    )


def dedupe_rows(rows: list[dict]) -> list[dict]:
    out = {}
    for row in rows:
        if row.get("ticker") and row.get("transaction_date") and row.get("amount"):
            out[trade_key(row)] = row
    return list(out.values())


def extract_pdf_rows(content: bytes, filing: dict) -> tuple[list[dict], str]:
    text_rows: list[dict] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        pages = list(pdf.pages)
        for page in pages:
            text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
            text_rows.extend(parse_text_blob(text, filing))
            if len(text_rows) < 10:
                try:
                    for table in page.extract_tables() or []:
                        for cells in table or []:
                            row = parse_row_text(" ".join(normalise_space(x or "") for x in cells), filing)
                            if row:
                                text_rows.append(row)
                except Exception:
                    pass
        text_rows = dedupe_rows(text_rows)
        if text_rows:
            return text_rows, "text"

        print(f"No usable text-layer trades for {filing['disclosure_date']}; trying OCR fallback across {len(pages)} pages")
        ocr_rows: list[dict] = []
        for index, page in enumerate(pages, 1):
            text = ocr_page_text(page)
            if not text:
                continue
            found = parse_ocr_windows(text, filing)
            if found:
                print(f"OCR page {index}: {len(found)} mapped rows")
                ocr_rows.extend(found)
        return dedupe_rows(ocr_rows), "ocr"


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
            parsed, mode = extract_pdf_rows(response.content, filing)
            rows.extend(parsed)
            filing_status.append({
                "url": filing["url"], "disclosure_date": filing["disclosure_date"],
                "parsed_trades": len(parsed), "extraction": mode, "ok": True,
            })
        except Exception as exc:
            filing_status.append({
                "url": filing["url"], "disclosure_date": filing["disclosure_date"],
                "parsed_trades": 0, "ok": False, "error": str(exc)[:180],
            })

    merged = {}
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
            "key": "executive:donald-trump", "name": "Donald J. Trump",
            "role": "President of the United States", "chamber": "Executive",
            "source_label": "OGE Form 278-T", "source_url": FILINGS[0]["url"],
            "count": len(trades), "buys": buys, "sells": sells, "last": newest,
        }],
        "trades": trades,
        "filings": filing_status,
        "note": "Executive disclosures are separate from congressional STOCK Act data. Only transactions whose listed asset can be mapped unambiguously to a market ticker are published by Vestra.",
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Executive feed: {len(trades)} mapped trades ({buys} buys / {sells} sells), newest {newest}")


if __name__ == "__main__":
    main()
