"""Official/free physical-metals data adapters.

Best-effort sources, all public:
- CME Group COMEX warehouse/depository stock XLS reports.
- CFTC weekly Disaggregated COT futures-only file.
- Shanghai Gold Exchange benchmark-price page.
- World Gold Council central-bank reserve changes workbook (public download;
  may require a browser-like session and can fail with 403).

Every adapter returns explicit source/status metadata. Missing data stays missing;
no physical-market metric is inferred from price alone.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import logging
import re
from typing import Any

import pandas as pd
import requests

log = logging.getLogger("physical_metals")

UA = "Mozilla/5.0 (compatible; Finscanner/0.20; +https://github.com/possn/Finscanner)"
HEADERS = {"User-Agent": UA, "Accept": "*/*"}

CME_STOCK_URLS = {
    "gold": "https://www.cmegroup.com/delivery_reports/Gold_Stocks.xls",
    "silver": "https://www.cmegroup.com/delivery_reports/Silver_stocks.xls",
}
CFTC_DISAGG = "https://www.cftc.gov/dea/newcot/f_disagg.txt"
SGE_BENCHMARK = "https://en.sge.com.cn/data_BenchmarkPrice"
WGC_RESERVES_PAGE = "https://www.gold.org/goldhub/data/gold-reserves-by-country"
CME_DELIVERY_DAILY = "https://www.cmegroup.com/delivery_reports/MetalsIssuesAndStopsReport.pdf"


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _num(v: Any):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def _last_numeric(row):
    vals = [_num(v) for v in row]
    vals = [v for v in vals if v is not None]
    return vals[-1] if vals else None


def fetch_cme_stocks(kind: str) -> dict:
    url = CME_STOCK_URLS[kind]
    out = {"source": "CME Group", "source_url": url, "fetched_at": _now(), "status": "unavailable"}
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        r.raise_for_status()
        # XLS is legacy BIFF; xlrd is declared in requirements.
        df = pd.read_excel(io.BytesIO(r.content), header=None, engine="xlrd")
        text_rows = []
        for _, row in df.iterrows():
            text = " ".join(str(x) for x in row.tolist() if not pd.isna(x)).upper()
            text_rows.append((text, row.tolist()))

        registered = eligible = total = pledged = None
        # Prefer explicit summary rows.
        for text, row in text_rows:
            if "TOTAL REGISTERED" in text or ("REGISTERED" in text and "TOTAL" in text):
                registered = _last_numeric(row) or registered
            if "TOTAL ELIGIBLE" in text or ("ELIGIBLE" in text and "TOTAL" in text):
                eligible = _last_numeric(row) or eligible
            if "TOTAL PLEDGED" in text or ("PLEDGED" in text and "TOTAL" in text):
                pledged = _last_numeric(row) or pledged
            if re.search(r"\bGRAND TOTAL\b|\bTOTAL STOCK", text):
                total = _last_numeric(row) or total

        # Fallback: discover columns named REGISTERED / ELIGIBLE and use a TOTAL row.
        if registered is None or eligible is None:
            header_idx = None
            reg_col = elig_col = pled_col = None
            for idx, row in df.iterrows():
                cells = [str(x).upper().strip() if not pd.isna(x) else "" for x in row.tolist()]
                for j, c in enumerate(cells):
                    if "REGISTERED" in c: reg_col = j
                    if "ELIGIBLE" in c: elig_col = j
                    if "PLEDGED" in c: pled_col = j
                if reg_col is not None or elig_col is not None:
                    header_idx = idx
                    break
            if header_idx is not None:
                for idx in range(len(df) - 1, header_idx, -1):
                    cells = [str(x).upper().strip() if not pd.isna(x) else "" for x in df.iloc[idx].tolist()]
                    label = " ".join(cells[:3])
                    if "TOTAL" in label:
                        if registered is None and reg_col is not None: registered = _num(df.iat[idx, reg_col])
                        if eligible is None and elig_col is not None: eligible = _num(df.iat[idx, elig_col])
                        if pledged is None and pled_col is not None: pledged = _num(df.iat[idx, pled_col])
                        break

        if total is None and registered is not None and eligible is not None:
            total = registered + eligible
        if registered is None and eligible is None:
            raise ValueError("CME XLS parsed but summary inventory fields were not found")

        unit = "troy oz"
        out.update({
            "status": "ok",
            "registered_oz": round(registered, 2) if registered is not None else None,
            "eligible_oz": round(eligible, 2) if eligible is not None else None,
            "pledged_oz": round(pledged, 2) if pledged is not None else None,
            "total_oz": round(total, 2) if total is not None else None,
            "unit": unit,
        })
    except Exception as e:
        out["error"] = str(e)[:240]
        log.warning("CME %s stocks unavailable: %s", kind, e)
    return out


def fetch_cftc_gold_positioning() -> dict:
    out = {"source": "CFTC Disaggregated COT", "source_url": CFTC_DISAGG, "fetched_at": _now(), "status": "unavailable"}
    try:
        r = requests.get(CFTC_DISAGG, headers=HEADERS, timeout=25)
        r.raise_for_status()
        rows = list(csv.reader(io.StringIO(r.text)))
        gold = next(row for row in rows if row and row[0].strip().upper().startswith("GOLD - COMMODITY EXCHANGE INC."))
        def f(one_based): return _num(gold[one_based - 1]) if len(gold) >= one_based else None
        oi = f(8); mm_long = f(14); mm_short = f(15); mm_spread = f(16)
        ch_long = f(62); ch_short = f(63)
        net = (mm_long - mm_short) if mm_long is not None and mm_short is not None else None
        net_pct = (net / oi * 100) if net is not None and oi else None
        week_delta_net = (ch_long - ch_short) if ch_long is not None and ch_short is not None else None
        # Transparent display gauge: clip managed-money net share of OI from -30..+30 to 0..100.
        gauge = max(0, min(100, 50 + (net_pct or 0) / 30 * 50)) if net_pct is not None else None
        if net_pct is None: label = "sem dados"
        elif net_pct >= 12: label = "managed money fortemente net long"
        elif net_pct >= 3: label = "managed money net long"
        elif net_pct <= -12: label = "managed money fortemente net short"
        elif net_pct <= -3: label = "managed money net short"
        else: label = "managed money próximo de neutro"
        out.update({
            "status": "ok", "report_date": gold[2].strip(), "open_interest": int(oi) if oi is not None else None,
            "managed_money_long": int(mm_long) if mm_long is not None else None,
            "managed_money_short": int(mm_short) if mm_short is not None else None,
            "managed_money_spreading": int(mm_spread) if mm_spread is not None else None,
            "managed_money_net": int(net) if net is not None else None,
            "managed_money_net_pct_oi": round(net_pct, 2) if net_pct is not None else None,
            "weekly_change_net": int(week_delta_net) if week_delta_net is not None else None,
            "display_gauge_0_100": round(gauge, 1) if gauge is not None else None,
            "label": label,
            "method": "Gauge visual = managed-money net / open-interest, clipped at ±30%; not a predictive score.",
        })
    except Exception as e:
        out["error"] = str(e)[:240]
        log.warning("CFTC positioning unavailable: %s", e)
    return out


def fetch_sge_benchmark() -> dict:
    out = {"source": "Shanghai Gold Exchange", "source_url": SGE_BENCHMARK, "fetched_at": _now(), "status": "unavailable"}
    try:
        r = requests.get(SGE_BENCHMARK, headers={**HEADERS, "Accept-Language": "en-US,en;q=0.9"}, timeout=25)
        r.raise_for_status()
        tables = pd.read_html(io.StringIO(r.text))
        best = None
        for df in tables:
            cols = " ".join(map(str, df.columns)).lower()
            if "benchmark price" in cols and "trade date" in cols:
                best = df; break
        if best is None:
            # tolerate the site returning a simple 4-col table without exact flattened column labels
            for df in tables:
                if df.shape[1] >= 4 and any("SHAU" in str(v) for v in df.astype(str).values.flatten()):
                    best = df; break
        if best is None or best.empty: raise ValueError("benchmark table not found")
        row = None
        for _, rr in best.iterrows():
            if any("SHAU" == str(v).strip().upper() for v in rr.tolist()): row = rr; break
        if row is None: row = best.iloc[0]
        vals = row.tolist()
        # Website order: Trade Date, Contract, AM, PM. Prefer PM when present.
        trade_date = str(vals[0]).strip()
        contract = str(vals[1]).strip() if len(vals) > 1 else "SHAU"
        am = _num(vals[2]) if len(vals) > 2 else None
        pm = _num(vals[3]) if len(vals) > 3 else None
        benchmark = pm if pm is not None else am
        if benchmark is None: raise ValueError("benchmark value not found")
        out.update({"status": "ok", "trade_date": trade_date, "contract": contract, "benchmark_cny_per_g": round(benchmark, 4), "am": am, "pm": pm})
    except Exception as e:
        out["error"] = str(e)[:240]
        log.warning("SGE benchmark unavailable: %s", e)
    return out



def fetch_cme_delivery_notices() -> dict:
    """Parse CME's official daily Metals Issues & Stops PDF.

    We expose delivery-notice counts for the standard COMEX gold and silver
    contracts only. A notice is a clearing/delivery event, not proof that metal
    left a vault; ounce-equivalent figures are therefore labelled as such.
    """
    out = {"source": "CME Group", "source_url": CME_DELIVERY_DAILY, "fetched_at": _now(), "status": "unavailable"}
    try:
        from pypdf import PdfReader
        r = requests.get(CME_DELIVERY_DAILY, headers=HEADERS, timeout=30)
        r.raise_for_status()
        reader = PdfReader(io.BytesIO(r.content))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        text = re.sub(r"[ \t]+", " ", text)

        business = re.search(r"BUSINESS DATE:\s*(\d{1,2}/\d{1,2}/\d{4})", text, re.I)
        business_date = business.group(1) if business else None

        def parse_contract(pattern: str, contract_oz: int):
            m = re.search(pattern, text, re.I)
            if not m:
                return {"status": "unavailable"}
            start = m.start()
            # The next EXCHANGE/CONTRACT block is a safe boundary.
            nxt = re.search(r"\n\s*EXCHANGE:\s*", text[m.end():], re.I)
            end = m.end() + nxt.start() if nxt else min(len(text), start + 12000)
            block = text[start:end]
            totals = re.findall(r"(?:^|\n)\s*TOTAL:\s*([0-9,]+)\s+([0-9,]+)", block, re.I)
            mtd = re.search(r"MONTH TO DATE:\s*([0-9,]+)", block, re.I)
            if not totals:
                return {"status": "unavailable", "error": "contract found but TOTAL not parsed"}
            issued, stopped = [int(x.replace(",", "")) for x in totals[-1]]
            # Issued and stopped should balance. Keep both so the UI can audit the parse.
            notices = min(issued, stopped) if issued and stopped else max(issued, stopped)
            return {
                "status": "ok", "issued": issued, "stopped": stopped,
                "daily_notices": notices,
                "daily_oz_equivalent": notices * contract_oz,
                "month_to_date_notices": int(mtd.group(1).replace(",", "")) if mtd else None,
                "month_to_date_oz_equivalent": int(mtd.group(1).replace(",", "")) * contract_oz if mtd else None,
                "contract_oz": contract_oz,
            }

        gold = parse_contract(r"CONTRACT:\s*[^\n]*COMEX 100 GOLD FUTURES", 100)
        silver = parse_contract(r"CONTRACT:\s*[^\n]*COMEX 5000 SILVER FUTURES", 5000)
        if gold.get("status") != "ok" and silver.get("status") != "ok":
            raise ValueError("daily PDF downloaded but gold/silver delivery blocks were not parsed")
        out.update({"status": "ok", "business_date": business_date, "gold": gold, "silver": silver,
                    "method": "CME Issues & Stops. Ounce-equivalent = notices × standard contract size; not vault withdrawals."})
    except Exception as e:
        out["error"] = str(e)[:240]
        log.warning("CME delivery notices unavailable: %s", e)
    return out


def fetch_wgc_central_bank_changes() -> dict:
    out = {"source": "World Gold Council / IMF IFS", "source_url": WGC_RESERVES_PAGE, "fetched_at": _now(), "status": "unavailable"}
    try:
        s = requests.Session(); s.headers.update({**HEADERS, "Referer": WGC_RESERVES_PAGE})
        page = s.get(WGC_RESERVES_PAGE, timeout=25); page.raise_for_status()
        m = re.search(r'href=["\']([^"\']*Changes_latest[^"\']*\.xlsx)["\']', page.text, re.I)
        if not m: raise ValueError("WGC changes workbook link not found")
        url = requests.compat.urljoin(WGC_RESERVES_PAGE, m.group(1))
        r = s.get(url, timeout=30); r.raise_for_status()
        sheets = pd.read_excel(io.BytesIO(r.content), sheet_name=None)
        candidates = []
        for _, df in sheets.items():
            for i in range(min(25, len(df))):
                cells = [str(x) for x in df.iloc[i].tolist() if not pd.isna(x)]
                txt = " | ".join(cells).lower()
                if "country" in txt and ("change" in txt or "tonne" in txt):
                    tmp = pd.read_excel(io.BytesIO(r.content), sheet_name=_, header=i)
                    candidates.append(tmp)
                    break
        if not candidates: raise ValueError("WGC changes table not recognized")
        df = candidates[0]
        country_col = next((c for c in df.columns if "country" in str(c).lower()), df.columns[0])
        numeric_cols = [c for c in df.columns if c != country_col and pd.api.types.is_numeric_dtype(df[c])]
        if not numeric_cols:
            for c in df.columns:
                if c != country_col:
                    conv = pd.to_numeric(df[c], errors="coerce")
                    if conv.notna().sum() >= 3:
                        df[c] = conv; numeric_cols.append(c)
        if not numeric_cols: raise ValueError("WGC numeric change column not found")
        # Use the right-most numeric column as latest period.
        change_col = numeric_cols[-1]
        clean = df[[country_col, change_col]].dropna()
        clean = clean[pd.to_numeric(clean[change_col], errors="coerce").notna()].copy()
        clean[change_col] = pd.to_numeric(clean[change_col], errors="coerce")
        buyers = clean.sort_values(change_col, ascending=False).head(6)
        sellers = clean.sort_values(change_col, ascending=True).head(6)
        out.update({
            "status": "ok", "period": str(change_col), "workbook_url": url,
            "buyers": [{"country": str(r[country_col]), "tonnes": round(float(r[change_col]), 1)} for _, r in buyers.iterrows() if float(r[change_col]) > 0],
            "sellers": [{"country": str(r[country_col]), "tonnes": round(float(r[change_col]), 1)} for _, r in sellers.iterrows() if float(r[change_col]) < 0],
        })
    except Exception as e:
        out["error"] = str(e)[:240]
        log.warning("WGC central bank changes unavailable: %s", e)
    return out


def build_physical_payload() -> dict:
    return {
        "generated_at": _now(),
        "comex": {"gold": fetch_cme_stocks("gold"), "silver": fetch_cme_stocks("silver")},
        "deliveries": fetch_cme_delivery_notices(),
        "positioning": {"gold": fetch_cftc_gold_positioning()},
        "shanghai": {"gold_benchmark": fetch_sge_benchmark()},
        "central_banks": fetch_wgc_central_bank_changes(),
    }
