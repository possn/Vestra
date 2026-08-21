"""
metals.py — precious/industrial metals tracker, free data only.

Source: Yahoo Finance futures/ETF tickers via yfinance (same library used
for equities — no separate API or key needed).

Coverage decisions, stated explicitly:
  - Gold, silver, copper, platinum, palladium: tracked via their COMEX/
    NYMEX front-month futures tickers (GC=F, SI=F, HG=F, PL=F, PA=F).
    Futures prices, not spot — they track spot closely but are NOT
    identical (contango/backwardation, roll costs). Do not present this
    as "the spot price".
  - Uranium: there is no free, direct spot-uranium ticker on Yahoo
    Finance (uranium doesn't trade on a public futures exchange the way
    gold does — it's largely an OTC/term-contract market). URA (Global X
    Uranium ETF) is used as an equity-basket PROXY, not a uranium price.
    This is a real limitation, not an oversight — flagged in the output.
  - No "stress score" or composite indicator is computed for metals.
    Unlike the equity score (built from transparent, well-known ratios),
    a genuine COMEX-stress-type metric needs data (inventories, lease
    rates, delivery notices) that isn't available for free — fabricating
    a 0-100 number without that data would be a fake precision claim.
    This module reports price, daily change, and realized volatility
    only — nothing dressed up as more than it is.
"""
from __future__ import annotations

import datetime
import logging

import yfinance as yf

from physical_metals import build_physical_payload

log = logging.getLogger("metals")

INSTRUMENTS = [
    {
        "ticker": "GC=F", "label": "Ouro", "kind": "futures", "unit": "USD/oz",
        "context": (
            "Os bancos centrais têm sido compradores líquidos de ouro de forma "
            "consistente desde cerca de 2010, com China, Turquia, Índia e Polónia "
            "entre os maiores compradores da última década — uma tendência "
            "estrutural bem documentada, não um evento pontual. O Finscanner não "
            "calcula estes números (exigem dados do FMI/IFS sem API gratuita "
            "fiável); para os números trimestrais mais recentes, consulta as "
            "fontes oficiais abaixo."
        ),
        "context_links": [
            {"label": "World Gold Council — Gold Reserves by Country", "url": "https://www.gold.org/goldhub/data/gold-reserves-by-country"},
            {"label": "World Gold Council — Central Bank Gold Reserves Survey", "url": "https://www.gold.org/goldhub/data/central-bank-gold-reserves-survey-2025"},
        ],
    },
    {"ticker": "SI=F", "label": "Prata", "kind": "futures", "unit": "USD/oz"},
    {"ticker": "HG=F", "label": "Cobre", "kind": "futures", "unit": "USD/lb"},
    {"ticker": "PL=F", "label": "Platina", "kind": "futures", "unit": "USD/oz"},
    {"ticker": "PA=F", "label": "Paládio", "kind": "futures", "unit": "USD/oz"},
    {"ticker": "URA", "label": "Urânio (proxy: Global X Uranium ETF)", "kind": "etf_proxy", "unit": "USD"},
]


def fetch_metal(ticker: str, days: int = 365):
    try:
        hist = yf.Ticker(ticker).history(period=f"{days}d")
        if hist.empty:
            return None
        closes = hist["Close"].dropna()
        if len(closes) < 2:
            return None

        last = float(closes.iloc[-1])
        prev = float(closes.iloc[-2])
        day_change_pct = (last - prev) / prev * 100 if prev else None

        returns = closes.pct_change().dropna()
        # annualized realized volatility from daily returns in the window
        vol_annualized_pct = float(returns.std() * (252 ** 0.5) * 100) if len(returns) > 5 else None

        closes_90d = closes.tail(90)
        sma_200 = float(closes.tail(200).mean()) if len(closes) >= 60 else None
        vs_200d_pct = ((last - sma_200) / sma_200 * 100) if sma_200 else None
        low_1y = float(closes.min())
        high_1y = float(closes.max())
        position_52w_pct = ((last - low_1y) / (high_1y - low_1y) * 100) if high_1y > low_1y else None
        first_of_year = closes[closes.index.year == closes.index[-1].year]
        change_ytd_pct = ((last - float(first_of_year.iloc[0])) / float(first_of_year.iloc[0]) * 100) if len(first_of_year) > 1 else None
        change_1y_pct = ((last - float(closes.iloc[0])) / float(closes.iloc[0]) * 100) if len(closes) > 200 else None

        return {
            "price": round(last, 3),
            "day_change_pct": round(day_change_pct, 2) if day_change_pct is not None else None,
            "range_90d_low": round(float(closes_90d.min()), 3),
            "range_90d_high": round(float(closes_90d.max()), 3),
            "range_1y_low": round(low_1y, 3),
            "range_1y_high": round(high_1y, 3),
            "sma_200": round(sma_200, 3) if sma_200 is not None else None,
            "vs_200d_pct": round(vs_200d_pct, 1) if vs_200d_pct is not None else None,
            "position_52w_pct": round(position_52w_pct, 1) if position_52w_pct is not None else None,
            "change_ytd_pct": round(change_ytd_pct, 1) if change_ytd_pct is not None else None,
            "change_1y_pct": round(change_1y_pct, 1) if change_1y_pct is not None else None,
            "volatility_annualized_pct": round(vol_annualized_pct, 1) if vol_annualized_pct is not None else None,
        }
    except Exception as e:
        log.warning("%s: fetch failed (%s)", ticker, e)
        return None


def build_metals_payload() -> dict:
    rows = []
    for inst in INSTRUMENTS:
        data = fetch_metal(inst["ticker"])
        rows.append({**inst, "data": data})

    physical = build_physical_payload()

    # Shanghai premium proxy: SGE SHAUs benchmark (CNY/g) converted to USD/oz
    # against the COMEX front-month gold future. This is NOT a true Shanghai-London
    # premium; it is explicitly labelled as a cross-market proxy.
    sge = physical.get("shanghai", {}).get("gold_benchmark", {})
    gold = next((r for r in rows if r.get("ticker") == "GC=F"), None)
    try:
        fx_hist = yf.Ticker("CNY=X").history(period="5d")
        cny_per_usd = float(fx_hist["Close"].dropna().iloc[-1]) if not fx_hist.empty else None
    except Exception:
        cny_per_usd = None
    if sge.get("status") == "ok" and cny_per_usd and gold and gold.get("data", {}).get("price"):
        sge_usd_oz = float(sge["benchmark_cny_per_g"]) * 31.1034768 / cny_per_usd
        comex = float(gold["data"]["price"])
        sge["cny_per_usd"] = round(cny_per_usd, 4)
        sge["benchmark_usd_per_oz_proxy"] = round(sge_usd_oz, 2)
        sge["premium_vs_comex_front_pct"] = round((sge_usd_oz / comex - 1) * 100, 2) if comex else None
        sge["premium_method"] = "SGE benchmark converted at CNY/USD vs COMEX front-month future; proxy, not Shanghai-London spot premium."

    gaps = []
    if physical.get("comex", {}).get("gold", {}).get("status") != "ok": gaps.append("COMEX gold registered/eligible inventory")
    if physical.get("comex", {}).get("silver", {}).get("status") != "ok": gaps.append("COMEX silver registered/eligible inventory")
    if physical.get("positioning", {}).get("gold", {}).get("status") != "ok": gaps.append("CFTC managed-money positioning")
    if sge.get("status") != "ok": gaps.append("Shanghai Gold Exchange benchmark")
    if physical.get("central_banks", {}).get("status") != "ok": gaps.append("central-bank monthly flows (WGC workbook)")
    if physical.get("deliveries", {}).get("status") != "ok": gaps.append("COMEX daily delivery notices (CME Issues & Stops PDF)")
    gaps.append("paper-to-physical leverage / delivery-stress score: deliberately not derived without a defensible methodology")

    return {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "note": (
            "Preços de futuros (não spot) para ouro/prata/cobre/platina/paládio. "
            "Urânio é um proxy via ETF de mineradoras. A camada física e de deliveries usa fontes "
            "oficiais/gratuitas (CME, CFTC, SGE e, quando acessível, WGC). Cada bloco "
            "expõe a fonte e o estado; dados indisponíveis não são estimados."
        ),
        "ways_to_play": {
            "own_metal": ["GLD", "IAU", "GLDM"],
            "miners": ["GDX", "GDXJ", "NEM", "AEM", "KGC"],
            "royalty_streaming": ["FNV", "WPM", "RGLD"],
        },
        "physical": physical,
        "data_gaps": gaps,
        "instruments": rows,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(build_metals_payload(), indent=2))
