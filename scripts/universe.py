"""
universe.py — builds the daily ticker universe from free sources only.

US leg:      Yahoo Finance screener (via yfinance.screen), small/micro-cap,
             same approach as the existing stock-scanner project.
Intl legs:   UK + continental Europe constituent tables scraped from Wikipedia
             (public, no key, no rate limit). Australia is intentionally excluded. Suffixes map to Yahoo Finance's
             exchange convention so the same fetch pipeline works for
             every market.

Nothing here requires a paid API key. Network calls are wrapped so a
single failing source degrades the universe instead of crashing the run.
"""
from __future__ import annotations

import logging
import time
import json
import os
from dataclasses import dataclass
from io import StringIO

import pandas as pd
import requests
import yfinance as yf

# Logging is configured centrally by run.py (so all module logs land in
# the committed data/pipeline_log.txt). When this module is run directly
# in isolation, output falls back to Python's default "no handlers"
# behaviour — add a handler yourself if running standalone.
log = logging.getLogger("universe")

# ETF universe: yfinance/Yahoo has no free "screen all ETFs" endpoint
# comparable to the equity screener, and Yahoo's own `sector` field is
# usually blank for funds — so both the ticker list AND the sector label
# are curated by hand here rather than fetched. This is a deliberate
# trade-off: broad, liquid, well-known ETFs across the major GICS-style
# sectors plus a few broad-market/thematic/bond funds, small enough to
# maintain by hand, large enough to make the "procurar ETFs por setor"
# filter meaningful. Expense ratio and AI-exposure are still computed
# live from real data (fundamentals.py) — only the sector tag and the
# ticker list itself are static.
ETF_UNIVERSE: dict[str, dict[str, str]] = {
    # SPDR Select Sector — cleanly maps 1:1 to GICS sectors. All US-listed,
    # investing in US-sector companies, so region = United States.
    "XLK": {"sector": "Technology", "region": "United States"},
    "XLF": {"sector": "Financial Services", "region": "United States"},
    "XLE": {"sector": "Energy", "region": "United States"},
    "XLV": {"sector": "Healthcare", "region": "United States"},
    "XLI": {"sector": "Industrials", "region": "United States"},
    "XLY": {"sector": "Consumer Cyclical", "region": "United States"},
    "XLP": {"sector": "Consumer Defensive", "region": "United States"},
    "XLU": {"sector": "Utilities", "region": "United States"},
    "XLB": {"sector": "Basic Materials", "region": "United States"},
    "XLRE": {"sector": "Real Estate", "region": "United States"},
    "XLC": {"sector": "Communication Services", "region": "United States"},
    # Broad market
    "SPY": {"sector": "Broad Market", "region": "United States"},
    "VOO": {"sector": "Broad Market", "region": "United States"},
    "IVV": {"sector": "Broad Market", "region": "United States"},
    "VTI": {"sector": "Broad Market", "region": "United States"},
    "QQQ": {"sector": "Broad Market", "region": "United States"},
    "DIA": {"sector": "Broad Market", "region": "United States"},
    "IWM": {"sector": "Small Cap", "region": "United States"},
    # International / regional — region IS the point of these funds
    "EFA": {"sector": "Broad Market", "region": "International Developed"},
    "VEA": {"sector": "Broad Market", "region": "International Developed"},
    "EEM": {"sector": "Broad Market", "region": "Emerging Markets"},
    "VWO": {"sector": "Broad Market", "region": "Emerging Markets"},
    "EWU": {"sector": "Broad Market", "region": "United Kingdom"},
    "EWG": {"sector": "Broad Market", "region": "Germany"},
    "EWJ": {"sector": "Broad Market", "region": "Japan"},
    # Thematic / sector-adjacent (mostly US-listed & US-heavy holdings)
    "SMH": {"sector": "Semiconductors", "region": "Global"},
    "SOXX": {"sector": "Semiconductors", "region": "United States"},
    "ARKK": {"sector": "Innovation/Growth", "region": "Global"},
    "SKYY": {"sector": "Cloud Computing", "region": "United States"},
    "ROBO": {"sector": "Robotics & AI", "region": "Global"},
    "HACK": {"sector": "Cybersecurity", "region": "Global"},
    "IBB": {"sector": "Biotechnology", "region": "United States"},
    "XBI": {"sector": "Biotechnology", "region": "United States"},
    "ITA": {"sector": "Aerospace & Defense", "region": "United States"},
    "TAN": {"sector": "Solar/Clean Energy", "region": "Global"},
    "URA": {"sector": "Uranium", "region": "Global"},
    # Bonds / fixed income — US treasury/corporate unless noted
    "AGG": {"sector": "Bonds", "region": "United States"},
    "BND": {"sector": "Bonds", "region": "United States"},
    "TLT": {"sector": "Bonds (Long Treasury)", "region": "United States"},
    "SHY": {"sector": "Bonds (Short Treasury)", "region": "United States"},
    "LQD": {"sector": "Bonds (Corporate)", "region": "United States"},
    "HYG": {"sector": "Bonds (High Yield)", "region": "United States"},
    # Commodities proxies (metals themselves are covered separately in metals.py)
    "GLD": {"sector": "Commodities", "region": "Global"},
    "SLV": {"sector": "Commodities", "region": "Global"},
    "USO": {"sector": "Commodities", "region": "Global"},
    # Expanded thematic / style coverage for Funds discovery
    "AIQ": {"sector": "Artificial Intelligence", "region": "Global", "theme": "AI", "style": "Growth"},
    "BOTZ": {"sector": "Robotics & AI", "region": "Global", "theme": "AI", "style": "Growth"},
    "IRBO": {"sector": "Robotics & AI", "region": "Global", "theme": "AI", "style": "Growth"},
    "CIBR": {"sector": "Cybersecurity", "region": "Global", "theme": "Cybersecurity", "style": "Growth"},
    "PPA": {"sector": "Aerospace & Defense", "region": "United States", "theme": "Defense", "style": "Broad"},
    "XAR": {"sector": "Aerospace & Defense", "region": "United States", "theme": "Defense", "style": "Broad"},
    "URNM": {"sector": "Uranium", "region": "Global", "theme": "Nuclear", "style": "Broad"},
    "NLR": {"sector": "Uranium/Nuclear", "region": "Global", "theme": "Nuclear", "style": "Broad"},
    "ICLN": {"sector": "Clean Energy", "region": "Global", "theme": "Clean Energy", "style": "Growth"},
    "QCLN": {"sector": "Clean Energy", "region": "United States", "theme": "Clean Energy", "style": "Growth"},
    "PBW": {"sector": "Clean Energy", "region": "United States", "theme": "Clean Energy", "style": "Growth"},
    "IAU": {"sector": "Commodities", "region": "Global", "theme": "Gold", "style": "Broad"},
    "GDX": {"sector": "Gold Miners", "region": "Global", "theme": "Gold", "style": "Broad"},
    "GDXJ": {"sector": "Gold Miners", "region": "Global", "theme": "Gold", "style": "Small Cap"},
    "SCHD": {"sector": "Broad Market", "region": "United States", "theme": "", "style": "Dividend"},
    "VIG": {"sector": "Broad Market", "region": "United States", "theme": "", "style": "Dividend"},
    "VYM": {"sector": "Broad Market", "region": "United States", "theme": "", "style": "Dividend"},
    "DGRO": {"sector": "Broad Market", "region": "United States", "theme": "", "style": "Dividend"},
    "VUG": {"sector": "Broad Market", "region": "United States", "theme": "", "style": "Growth"},
    "SCHG": {"sector": "Broad Market", "region": "United States", "theme": "", "style": "Growth"},
    "QQQM": {"sector": "Broad Market", "region": "United States", "theme": "", "style": "Growth"},
    "VB": {"sector": "Small Cap", "region": "United States", "theme": "", "style": "Small Cap"},
    "IJR": {"sector": "Small Cap", "region": "United States", "theme": "", "style": "Small Cap"},
    "SCHA": {"sector": "Small Cap", "region": "United States", "theme": "", "style": "Small Cap"},
    "VGK": {"sector": "Broad Market", "region": "Europe", "theme": "", "style": "Broad"},
    "IEUR": {"sector": "Broad Market", "region": "Europe", "theme": "", "style": "Broad"},
    "EZU": {"sector": "Broad Market", "region": "Europe", "theme": "", "style": "Broad"},
    "FEZ": {"sector": "Broad Market", "region": "Europe", "theme": "", "style": "Broad"},
    "ACWX": {"sector": "Broad Market", "region": "Global", "theme": "", "style": "Broad"},
    "VEU": {"sector": "Broad Market", "region": "Global", "theme": "", "style": "Broad"},
    "VXUS": {"sector": "Broad Market", "region": "Global", "theme": "", "style": "Broad"},
    "ACWI": {"sector": "Broad Market", "region": "Global", "theme": "", "style": "Broad"},
    "VT": {"sector": "Broad Market", "region": "Global", "theme": "", "style": "Broad"},
    "BNDX": {"sector": "Bonds", "region": "Global", "theme": "", "style": "Bonds"},
}


# v0.87 — Global ETF catalogue layer.
#
# The catalogue is deliberately broader than the daily Yahoo fetch set. It gives
# the PWA a useful discovery universe even when a quote endpoint fails, while the
# pipeline enriches a rotating subset with live TER/AUM/holdings every day. This
# avoids making the daily Action excessively slow and lets coverage improve over
# time. Metadata-only rows are clearly marked in the UI and are never used as if
# TER/AUM/holdings were observed facts.
_GLOBAL_ETF_EXPANSION: dict[str, dict[str, str]] = {
    # US broad / factors / styles
    "SCHB": {"sector":"Broad Market","region":"United States","style":"Broad"},
    "ITOT": {"sector":"Broad Market","region":"United States","style":"Broad"},
    "SPLG": {"sector":"Broad Market","region":"United States","style":"Broad"},
    "RSP": {"sector":"Broad Market","region":"United States","style":"Broad"},
    "USMV": {"sector":"Broad Market","region":"United States","style":"Broad"},
    "QUAL": {"sector":"Broad Market","region":"United States","style":"Broad"},
    "MTUM": {"sector":"Broad Market","region":"United States","style":"Growth"},
    "VLUE": {"sector":"Broad Market","region":"United States","style":"Value"},
    "VTV": {"sector":"Broad Market","region":"United States","style":"Value"},
    "SCHV": {"sector":"Broad Market","region":"United States","style":"Value"},
    "IVE": {"sector":"Broad Market","region":"United States","style":"Value"},
    "IWF": {"sector":"Broad Market","region":"United States","style":"Growth"},
    "IWD": {"sector":"Broad Market","region":"United States","style":"Value"},
    "SPYG": {"sector":"Broad Market","region":"United States","style":"Growth"},
    "SPYV": {"sector":"Broad Market","region":"United States","style":"Value"},
    "VXF": {"sector":"Broad Market","region":"United States","style":"Broad"},
    "MDY": {"sector":"Mid Cap","region":"United States","style":"Broad"},
    "VO": {"sector":"Mid Cap","region":"United States","style":"Broad"},
    "IJH": {"sector":"Mid Cap","region":"United States","style":"Broad"},
    "IJS": {"sector":"Small Cap","region":"United States","style":"Small Cap"},
    "IWO": {"sector":"Small Cap","region":"United States","style":"Small Cap"},
    "IWN": {"sector":"Small Cap","region":"United States","style":"Small Cap"},
    "VBR": {"sector":"Small Cap","region":"United States","style":"Small Cap"},
    "VBK": {"sector":"Small Cap","region":"United States","style":"Small Cap"},
    "AVUV": {"sector":"Small Cap","region":"United States","style":"Small Cap"},
    "CALF": {"sector":"Small Cap","region":"United States","style":"Small Cap"},
    # Dividend / income
    "HDV": {"sector":"Broad Market","region":"United States","style":"Dividend"},
    "SDY": {"sector":"Broad Market","region":"United States","style":"Dividend"},
    "NOBL": {"sector":"Broad Market","region":"United States","style":"Dividend"},
    "DGRW": {"sector":"Broad Market","region":"United States","style":"Dividend"},
    "SPHD": {"sector":"Broad Market","region":"United States","style":"Dividend"},
    "JEPI": {"sector":"Broad Market","region":"United States","style":"Dividend"},
    "JEPQ": {"sector":"Broad Market","region":"United States","style":"Dividend"},
    "DIVO": {"sector":"Broad Market","region":"United States","style":"Dividend"},
    # Global / ex-US / regions
    "IXUS": {"sector":"Broad Market","region":"Global ex-US","style":"Broad"},
    "SCHF": {"sector":"Broad Market","region":"International Developed","style":"Broad"},
    "IDEV": {"sector":"Broad Market","region":"International Developed","style":"Broad"},
    "IEFA": {"sector":"Broad Market","region":"International Developed","style":"Broad"},
    "EFV": {"sector":"Broad Market","region":"International Developed","style":"Value"},
    "EFG": {"sector":"Broad Market","region":"International Developed","style":"Growth"},
    "VYMI": {"sector":"Broad Market","region":"Global ex-US","style":"Dividend"},
    "VIGI": {"sector":"Broad Market","region":"Global ex-US","style":"Dividend"},
    "DNL": {"sector":"Broad Market","region":"Global ex-US","style":"Growth"},
    "AAXJ": {"sector":"Broad Market","region":"Asia ex-Japan","style":"Broad"},
    "VPL": {"sector":"Broad Market","region":"Asia Pacific","style":"Broad"},
    "AIA": {"sector":"Broad Market","region":"Asia","style":"Broad"},
    "MCHI": {"sector":"Broad Market","region":"China","style":"Broad"},
    "FXI": {"sector":"Broad Market","region":"China","style":"Broad"},
    "KWEB": {"sector":"Internet","region":"China","theme":"AI","style":"Growth"},
    "ASHR": {"sector":"Broad Market","region":"China","style":"Broad"},
    "INDA": {"sector":"Broad Market","region":"India","style":"Broad"},
    "EPI": {"sector":"Broad Market","region":"India","style":"Broad"},
    "EWY": {"sector":"Broad Market","region":"South Korea","style":"Broad"},
    "EWT": {"sector":"Broad Market","region":"Taiwan","style":"Broad"},
    "EWH": {"sector":"Broad Market","region":"Hong Kong","style":"Broad"},
    "EWQ": {"sector":"Broad Market","region":"France","style":"Broad"},
    "EWI": {"sector":"Broad Market","region":"Italy","style":"Broad"},
    "EWP": {"sector":"Broad Market","region":"Spain","style":"Broad"},
    "EWN": {"sector":"Broad Market","region":"Netherlands","style":"Broad"},
    "EWL": {"sector":"Broad Market","region":"Switzerland","style":"Broad"},
    "EWD": {"sector":"Broad Market","region":"Sweden","style":"Broad"},
    "NORW": {"sector":"Broad Market","region":"Norway","style":"Broad"},
    "EPOL": {"sector":"Broad Market","region":"Poland","style":"Broad"},
    "GREK": {"sector":"Broad Market","region":"Greece","style":"Broad"},
    "TUR": {"sector":"Broad Market","region":"Turkey","style":"Broad"},
    "EWW": {"sector":"Broad Market","region":"Mexico","style":"Broad"},
    "EWZ": {"sector":"Broad Market","region":"Brazil","style":"Broad"},
    "ARGT": {"sector":"Broad Market","region":"Argentina","style":"Broad"},
    "ECH": {"sector":"Broad Market","region":"Chile","style":"Broad"},
    "EWC": {"sector":"Broad Market","region":"Canada","style":"Broad"},
    # Technology / semiconductors / AI / robotics / cyber
    "VGT": {"sector":"Technology","region":"United States","style":"Growth"},
    "IYW": {"sector":"Technology","region":"United States","style":"Growth"},
    "FTEC": {"sector":"Technology","region":"United States","style":"Growth"},
    "IGV": {"sector":"Software","region":"United States","style":"Growth"},
    "FDN": {"sector":"Internet","region":"United States","style":"Growth"},
    "CLOU": {"sector":"Cloud Computing","region":"Global","theme":"AI","style":"Growth"},
    "WCLD": {"sector":"Cloud Computing","region":"Global","theme":"AI","style":"Growth"},
    "BUG": {"sector":"Cybersecurity","region":"Global","theme":"Cybersecurity","style":"Growth"},
    "IHAK": {"sector":"Cybersecurity","region":"Global","theme":"Cybersecurity","style":"Growth"},
    "ARKQ": {"sector":"Robotics & AI","region":"Global","theme":"Robotics","style":"Growth"},
    "ROBT": {"sector":"Robotics & AI","region":"Global","theme":"Robotics","style":"Growth"},
    "THNQ": {"sector":"Artificial Intelligence","region":"Global","theme":"AI","style":"Growth"},
    "CHAT": {"sector":"Artificial Intelligence","region":"Global","theme":"AI","style":"Growth"},
    "ARTY": {"sector":"Artificial Intelligence","region":"Global","theme":"AI","style":"Growth"},
    "SOXQ": {"sector":"Semiconductors","region":"United States","theme":"Semiconductors","style":"Growth"},
    "XSD": {"sector":"Semiconductors","region":"United States","theme":"Semiconductors","style":"Growth"},
    "PSI": {"sector":"Semiconductors","region":"United States","theme":"Semiconductors","style":"Growth"},
    "FTXL": {"sector":"Semiconductors","region":"United States","theme":"Semiconductors","style":"Growth"},
    # Defense / industrial / infrastructure
    "DFEN": {"sector":"Aerospace & Defense","region":"United States","theme":"Defense","style":"Growth"},
    "SHLD": {"sector":"Aerospace & Defense","region":"Global","theme":"Defense","style":"Broad"},
    "VIS": {"sector":"Industrials","region":"United States","style":"Broad"},
    "FIDU": {"sector":"Industrials","region":"United States","style":"Broad"},
    "PAVE": {"sector":"Infrastructure","region":"United States","theme":"Infrastructure","style":"Broad"},
    "IFRA": {"sector":"Infrastructure","region":"United States","theme":"Infrastructure","style":"Broad"},
    "IGF": {"sector":"Infrastructure","region":"Global","theme":"Infrastructure","style":"Broad"},
    # Energy / uranium / clean energy
    "VDE": {"sector":"Energy","region":"United States","theme":"Energy","style":"Broad"},
    "IYE": {"sector":"Energy","region":"United States","theme":"Energy","style":"Broad"},
    "FENY": {"sector":"Energy","region":"United States","theme":"Energy","style":"Broad"},
    "XOP": {"sector":"Oil & Gas E&P","region":"United States","theme":"Energy","style":"Broad"},
    "OIH": {"sector":"Oil Services","region":"Global","theme":"Energy","style":"Broad"},
    "AMLP": {"sector":"Midstream Energy","region":"United States","theme":"Energy","style":"Dividend"},
    "MLPX": {"sector":"Midstream Energy","region":"United States","theme":"Energy","style":"Dividend"},
    "URA": {"sector":"Uranium","region":"Global","theme":"Nuclear","style":"Broad"},
    "URNJ": {"sector":"Uranium","region":"Global","theme":"Nuclear","style":"Small Cap"},
    "UTES": {"sector":"Utilities","region":"United States","theme":"Energy","style":"Broad"},
    "PBW": {"sector":"Clean Energy","region":"United States","theme":"Clean Energy","style":"Growth"},
    "CNRG": {"sector":"Clean Energy","region":"Global","theme":"Clean Energy","style":"Growth"},
    "ACES": {"sector":"Clean Energy","region":"North America","theme":"Clean Energy","style":"Growth"},
    "FAN": {"sector":"Wind Energy","region":"Global","theme":"Clean Energy","style":"Growth"},
    # Healthcare / biotech
    "VHT": {"sector":"Healthcare","region":"United States","style":"Broad"},
    "IYH": {"sector":"Healthcare","region":"United States","style":"Broad"},
    "FHLC": {"sector":"Healthcare","region":"United States","style":"Broad"},
    "IHI": {"sector":"Medical Devices","region":"United States","style":"Growth"},
    "XPH": {"sector":"Pharmaceuticals","region":"United States","style":"Broad"},
    "ARKG": {"sector":"Genomics","region":"Global","theme":"Biotechnology","style":"Growth"},
    "GNOM": {"sector":"Genomics","region":"Global","theme":"Biotechnology","style":"Growth"},
    # Financial / REIT / consumer / materials
    "VFH": {"sector":"Financial Services","region":"United States","style":"Broad"},
    "IYF": {"sector":"Financial Services","region":"United States","style":"Broad"},
    "KBE": {"sector":"Banks","region":"United States","style":"Broad"},
    "KRE": {"sector":"Regional Banks","region":"United States","style":"Broad"},
    "VNQ": {"sector":"Real Estate","region":"United States","style":"Dividend"},
    "SCHH": {"sector":"Real Estate","region":"United States","style":"Dividend"},
    "IYR": {"sector":"Real Estate","region":"United States","style":"Dividend"},
    "REET": {"sector":"Real Estate","region":"Global","style":"Dividend"},
    "VCR": {"sector":"Consumer Cyclical","region":"United States","style":"Broad"},
    "VDC": {"sector":"Consumer Defensive","region":"United States","style":"Broad"},
    "XRT": {"sector":"Retail","region":"United States","style":"Broad"},
    "IYM": {"sector":"Basic Materials","region":"United States","style":"Broad"},
    "VAW": {"sector":"Basic Materials","region":"United States","style":"Broad"},
    "PICK": {"sector":"Metals & Mining","region":"Global","theme":"Metals","style":"Broad"},
    "COPX": {"sector":"Copper Miners","region":"Global","theme":"Metals","style":"Broad"},
    "LIT": {"sector":"Lithium & Battery","region":"Global","theme":"Clean Energy","style":"Growth"},
    # Gold / commodities
    "SGOL": {"sector":"Commodities","region":"Global","theme":"Gold","style":"Broad"},
    "BAR": {"sector":"Commodities","region":"Global","theme":"Gold","style":"Broad"},
    "GLDM": {"sector":"Commodities","region":"Global","theme":"Gold","style":"Broad"},
    "SIL": {"sector":"Silver Miners","region":"Global","theme":"Metals","style":"Broad"},
    "SILJ": {"sector":"Silver Miners","region":"Global","theme":"Metals","style":"Small Cap"},
    "DBC": {"sector":"Commodities","region":"Global","style":"Broad"},
    "PDBC": {"sector":"Commodities","region":"Global","style":"Broad"},
    # Bonds / cash
    "BIL": {"sector":"Bonds","region":"United States","style":"Bonds"},
    "SGOV": {"sector":"Bonds","region":"United States","style":"Bonds"},
    "VGSH": {"sector":"Bonds","region":"United States","style":"Bonds"},
    "IEF": {"sector":"Bonds","region":"United States","style":"Bonds"},
    "VGIT": {"sector":"Bonds","region":"United States","style":"Bonds"},
    "VGLT": {"sector":"Bonds","region":"United States","style":"Bonds"},
    "TIP": {"sector":"Bonds","region":"United States","style":"Bonds"},
    "SCHP": {"sector":"Bonds","region":"United States","style":"Bonds"},
    "VCIT": {"sector":"Bonds","region":"United States","style":"Bonds"},
    "VCSH": {"sector":"Bonds","region":"United States","style":"Bonds"},
    "JNK": {"sector":"Bonds","region":"United States","style":"Bonds"},
    "EMB": {"sector":"Bonds","region":"Emerging Markets","style":"Bonds"},
    "VWOB": {"sector":"Bonds","region":"Emerging Markets","style":"Bonds"},
    # Major UCITS / European listings (metadata catalogue; live quote enrichment when available)
    "CSPX.L": {"sector":"Broad Market","region":"United States","style":"Broad","ucits":"confirmed"},
    "VUAA.L": {"sector":"Broad Market","region":"United States","style":"Broad","ucits":"confirmed"},
    "VUSA.L": {"sector":"Broad Market","region":"United States","style":"Dividend","ucits":"confirmed"},
    "IUSA.L": {"sector":"Broad Market","region":"United States","style":"Dividend","ucits":"confirmed"},
    "SWDA.L": {"sector":"Broad Market","region":"Global","style":"Broad","ucits":"confirmed"},
    "IWDA.AS": {"sector":"Broad Market","region":"Global","style":"Broad","ucits":"confirmed"},
    "EUNL.DE": {"sector":"Broad Market","region":"Global","style":"Broad","ucits":"confirmed"},
    "VWCE.DE": {"sector":"Broad Market","region":"Global","style":"Broad","ucits":"confirmed"},
    "VWRL.L": {"sector":"Broad Market","region":"Global","style":"Dividend","ucits":"confirmed"},
    "SSAC.L": {"sector":"Broad Market","region":"Global","style":"Broad","ucits":"confirmed"},
    "IUSN.L": {"sector":"Small Cap","region":"Global","style":"Small Cap","ucits":"confirmed"},
    "EMIM.L": {"sector":"Broad Market","region":"Emerging Markets","style":"Broad","ucits":"confirmed"},
    "IS3N.DE": {"sector":"Broad Market","region":"Emerging Markets","style":"Broad","ucits":"confirmed"},
    "IEMA.L": {"sector":"Broad Market","region":"Emerging Markets","style":"Broad","ucits":"confirmed"},
    "IMEU.L": {"sector":"Broad Market","region":"Europe","style":"Broad","ucits":"confirmed"},
    "EXSA.DE": {"sector":"Broad Market","region":"Europe","style":"Broad","ucits":"confirmed"},
    "MEUD.PA": {"sector":"Broad Market","region":"Europe","style":"Broad","ucits":"confirmed"},
    "CNDX.L": {"sector":"Technology","region":"United States","style":"Growth","ucits":"confirmed"},
    "EQQQ.L": {"sector":"Technology","region":"United States","style":"Growth","ucits":"confirmed"},
    "IUIT.L": {"sector":"Technology","region":"United States","style":"Growth","ucits":"confirmed"},
    "SMH.L": {"sector":"Semiconductors","region":"Global","theme":"Semiconductors","style":"Growth","ucits":"confirmed"},
    "SEMI.L": {"sector":"Semiconductors","region":"Global","theme":"Semiconductors","style":"Growth","ucits":"confirmed"},
    "RBOT.L": {"sector":"Robotics & AI","region":"Global","theme":"Robotics","style":"Growth","ucits":"confirmed"},
    "AIAI.L": {"sector":"Artificial Intelligence","region":"Global","theme":"AI","style":"Growth","ucits":"confirmed"},
    "INRG.L": {"sector":"Clean Energy","region":"Global","theme":"Clean Energy","style":"Growth","ucits":"confirmed"},
    "IQQH.DE": {"sector":"Clean Energy","region":"Global","theme":"Clean Energy","style":"Growth","ucits":"confirmed"},
    "SGLN.L": {"sector":"Commodities","region":"Global","theme":"Gold","style":"Broad","ucits":"confirmed"},
    "PHAU.L": {"sector":"Commodities","region":"Global","theme":"Gold","style":"Broad","ucits":"confirmed"},
}

# Keep any richer metadata already present in the original core list.
for _ticker, _meta in _GLOBAL_ETF_EXPANSION.items():
    ETF_UNIVERSE.setdefault(_ticker, _meta)

# Core names are refreshed every day; the wider catalogue is refreshed in a
# deterministic rotation so Actions stay within a practical runtime.
ETF_CORE_TICKERS = frozenset(list(ETF_UNIVERSE.keys())[:79])


def etf_daily_fetch_tickers(limit: int = 70) -> list[str]:
    """Core ETFs + a rotating slice of the wider catalogue.

    All catalogue names remain visible in the PWA as metadata-only rows. The
    rotating enrichment provides live Yahoo fields without requiring hundreds
    of extra network calls every single day.
    """
    wider = sorted(set(ETF_UNIVERSE) - set(ETF_CORE_TICKERS))
    if not wider:
        return sorted(ETF_CORE_TICKERS)
    day = int(time.time() // 86400)
    start = (day * limit) % len(wider)
    rotated = wider[start:] + wider[:start]
    return sorted(set(ETF_CORE_TICKERS) | set(rotated[:limit]))

# Ticker-suffix -> region, for equities (where they trade, not just an
# abstract "market code"). Used to set row["region"] server-side so the
# frontend has one authoritative field instead of re-deriving it from the
# ticker string in JS.
EQUITY_REGION_BY_SUFFIX: dict[str, str] = {
    "": "United States",
    ".AX": "Australia",
    ".L": "United Kingdom",
    ".DE": "Germany",
    ".PA": "France",
    ".AS": "Netherlands",
    ".MC": "Spain",
    ".MI": "Italy",
    ".SW": "Switzerland",
    ".LS": "Portugal",
    ".ST": "Sweden",
    ".CO": "Denmark",
    ".WA": "Poland",
    ".TO": "Canada",
    ".OL": "Norway",
    ".HE": "Finland",
    ".VI": "Austria",
    ".BR": "Belgium",
}


def region_for_equity(ticker: str) -> str:
    for suffix, region in EQUITY_REGION_BY_SUFFIX.items():
        if suffix and ticker.endswith(suffix):
            return region
    return EQUITY_REGION_BY_SUFFIX[""]

HEADERS = {"User-Agent": "Finscanner/0.1 (personal research tool; contact: set-your-email-here)"}


@dataclass
class Market:
    name: str
    suffix: str  # Yahoo Finance ticker suffix, "" for US




# Curated equity discovery anchors.  These are not the whole market; they are
# a resilient seed layer for sectors/themes that users explicitly browse in the
# PWA.  The daily universe still comes from Yahoo/Wikipedia, while these names
# guarantee that important themes remain represented even when a screener or
# quote endpoint is temporarily incomplete.  Missing live fields are never
# fabricated; run.py can carry forward prior observed data or expose a
# metadata-only catalogue row until enrichment succeeds.
STOCK_DISCOVERY_CATALOG: dict[str, dict[str, str]] = {
    # Water
    "AWK": {"name":"American Water Works", "sector":"Utilities", "industry":"Utilities - Regulated Water", "theme":"Water", "region":"United States"},
    "XYL": {"name":"Xylem Inc.", "sector":"Industrials", "industry":"Specialty Industrial Machinery", "theme":"Water", "region":"United States"},
    "WMS": {"name":"Advanced Drainage Systems", "sector":"Industrials", "industry":"Building Products & Equipment", "theme":"Water", "region":"United States"},
    "BMI": {"name":"Badger Meter", "sector":"Technology", "industry":"Scientific & Technical Instruments", "theme":"Water", "region":"United States"},
    "MWA": {"name":"Mueller Water Products", "sector":"Industrials", "industry":"Specialty Industrial Machinery", "theme":"Water", "region":"United States"},
    "PNR": {"name":"Pentair", "sector":"Industrials", "industry":"Specialty Industrial Machinery", "theme":"Water", "region":"United States"},
    "ECL": {"name":"Ecolab", "sector":"Materials", "industry":"Specialty Chemicals", "theme":"Water", "region":"United States"},
    "CWCO": {"name":"Consolidated Water", "sector":"Utilities", "industry":"Utilities - Regulated Water", "theme":"Water", "region":"United States"},
    "AWR": {"name":"American States Water", "sector":"Utilities", "industry":"Utilities - Regulated Water", "theme":"Water", "region":"United States"},
    "SJW": {"name":"SJW Group", "sector":"Utilities", "industry":"Utilities - Regulated Water", "theme":"Water", "region":"United States"},
    # Agriculture / food chain
    "DE": {"name":"Deere & Company", "sector":"Industrials", "industry":"Farm & Heavy Construction Machinery", "theme":"Agriculture", "region":"United States"},
    "ADM": {"name":"Archer-Daniels-Midland", "sector":"Consumer Defensive", "industry":"Farm Products", "theme":"Agriculture", "region":"United States"},
    "BG": {"name":"Bunge Global", "sector":"Consumer Defensive", "industry":"Farm Products", "theme":"Agriculture", "region":"United States"},
    "CTVA": {"name":"Corteva", "sector":"Materials", "industry":"Agricultural Inputs", "theme":"Agriculture", "region":"United States"},
    "MOS": {"name":"The Mosaic Company", "sector":"Materials", "industry":"Agricultural Inputs", "theme":"Agriculture", "region":"United States"},
    "NTR": {"name":"Nutrien", "sector":"Materials", "industry":"Agricultural Inputs", "theme":"Agriculture", "region":"Canada"},
    "CF": {"name":"CF Industries", "sector":"Materials", "industry":"Agricultural Inputs", "theme":"Agriculture", "region":"United States"},
    "FMC": {"name":"FMC Corporation", "sector":"Materials", "industry":"Agricultural Inputs", "theme":"Agriculture", "region":"United States"},
    "CALM": {"name":"Cal-Maine Foods", "sector":"Consumer Defensive", "industry":"Farm Products", "theme":"Agriculture", "region":"United States"},
    "TSN": {"name":"Tyson Foods", "sector":"Consumer Defensive", "industry":"Farm Products", "theme":"Agriculture", "region":"United States"},
    # Healthcare
    "UNH": {"name":"UnitedHealth Group", "sector":"Healthcare", "industry":"Healthcare Plans", "theme":"Healthcare", "region":"United States"},
    "JNJ": {"name":"Johnson & Johnson", "sector":"Healthcare", "industry":"Drug Manufacturers - General", "theme":"Healthcare", "region":"United States"},
    "LLY": {"name":"Eli Lilly", "sector":"Healthcare", "industry":"Drug Manufacturers - General", "theme":"Healthcare", "region":"United States"},
    "MRK": {"name":"Merck & Co.", "sector":"Healthcare", "industry":"Drug Manufacturers - General", "theme":"Healthcare", "region":"United States"},
    "ABBV": {"name":"AbbVie", "sector":"Healthcare", "industry":"Drug Manufacturers - General", "theme":"Healthcare", "region":"United States"},
    "TMO": {"name":"Thermo Fisher Scientific", "sector":"Healthcare", "industry":"Diagnostics & Research", "theme":"Healthcare", "region":"United States"},
    "DHR": {"name":"Danaher", "sector":"Healthcare", "industry":"Diagnostics & Research", "theme":"Healthcare", "region":"United States"},
    "ISRG": {"name":"Intuitive Surgical", "sector":"Healthcare", "industry":"Medical Instruments & Supplies", "theme":"Healthcare", "region":"United States"},
    "SYK": {"name":"Stryker", "sector":"Healthcare", "industry":"Medical Devices", "theme":"Healthcare", "region":"United States"},
    "BSX": {"name":"Boston Scientific", "sector":"Healthcare", "industry":"Medical Devices", "theme":"Healthcare", "region":"United States"},
    "MDT": {"name":"Medtronic", "sector":"Healthcare", "industry":"Medical Devices", "theme":"Healthcare", "region":"United States"},
    "ABT": {"name":"Abbott Laboratories", "sector":"Healthcare", "industry":"Medical Devices", "theme":"Healthcare", "region":"United States"},
    # Biotech
    "AMGN": {"name":"Amgen", "sector":"Healthcare", "industry":"Biotechnology", "theme":"Biotech", "region":"United States"},
    "GILD": {"name":"Gilead Sciences", "sector":"Healthcare", "industry":"Biotechnology", "theme":"Biotech", "region":"United States"},
    "REGN": {"name":"Regeneron Pharmaceuticals", "sector":"Healthcare", "industry":"Biotechnology", "theme":"Biotech", "region":"United States"},
    "VRTX": {"name":"Vertex Pharmaceuticals", "sector":"Healthcare", "industry":"Biotechnology", "theme":"Biotech", "region":"United States"},
    "BIIB": {"name":"Biogen", "sector":"Healthcare", "industry":"Biotechnology", "theme":"Biotech", "region":"United States"},
    "MRNA": {"name":"Moderna", "sector":"Healthcare", "industry":"Biotechnology", "theme":"Biotech", "region":"United States"},
    "BNTX": {"name":"BioNTech", "sector":"Healthcare", "industry":"Biotechnology", "theme":"Biotech", "region":"Germany"},
    "CRSP": {"name":"CRISPR Therapeutics", "sector":"Healthcare", "industry":"Biotechnology", "theme":"Biotech", "region":"Switzerland"},
    "NTLA": {"name":"Intellia Therapeutics", "sector":"Healthcare", "industry":"Biotechnology", "theme":"Biotech", "region":"United States"},
    "BEAM": {"name":"Beam Therapeutics", "sector":"Healthcare", "industry":"Biotechnology", "theme":"Biotech", "region":"United States"},
    # Defense
    "LMT": {"name":"Lockheed Martin", "sector":"Industrials", "industry":"Aerospace & Defense", "theme":"Defense", "region":"United States"},
    "NOC": {"name":"Northrop Grumman", "sector":"Industrials", "industry":"Aerospace & Defense", "theme":"Defense", "region":"United States"},
    "RTX": {"name":"RTX Corporation", "sector":"Industrials", "industry":"Aerospace & Defense", "theme":"Defense", "region":"United States"},
    "GD": {"name":"General Dynamics", "sector":"Industrials", "industry":"Aerospace & Defense", "theme":"Defense", "region":"United States"},
    "LHX": {"name":"L3Harris Technologies", "sector":"Industrials", "industry":"Aerospace & Defense", "theme":"Defense", "region":"United States"},
    "HII": {"name":"Huntington Ingalls", "sector":"Industrials", "industry":"Aerospace & Defense", "theme":"Defense", "region":"United States"},
    "BA.L": {"name":"BAE Systems", "sector":"Industrials", "industry":"Aerospace & Defense", "theme":"Defense", "region":"United Kingdom"},
    "RHM.DE": {"name":"Rheinmetall", "sector":"Industrials", "industry":"Aerospace & Defense", "theme":"Defense", "region":"Europe"},
    # Semiconductors
    "NVDA": {"name":"NVIDIA", "sector":"Technology", "industry":"Semiconductors", "theme":"Semiconductors", "region":"United States"},
    "AMD": {"name":"Advanced Micro Devices", "sector":"Technology", "industry":"Semiconductors", "theme":"Semiconductors", "region":"United States"},
    "AVGO": {"name":"Broadcom", "sector":"Technology", "industry":"Semiconductors", "theme":"Semiconductors", "region":"United States"},
    "QCOM": {"name":"Qualcomm", "sector":"Technology", "industry":"Semiconductors", "theme":"Semiconductors", "region":"United States"},
    "TXN": {"name":"Texas Instruments", "sector":"Technology", "industry":"Semiconductors", "theme":"Semiconductors", "region":"United States"},
    "MU": {"name":"Micron Technology", "sector":"Technology", "industry":"Semiconductors", "theme":"Semiconductors", "region":"United States"},
    "AMAT": {"name":"Applied Materials", "sector":"Technology", "industry":"Semiconductor Equipment & Materials", "theme":"Semiconductors", "region":"United States"},
    "LRCX": {"name":"Lam Research", "sector":"Technology", "industry":"Semiconductor Equipment & Materials", "theme":"Semiconductors", "region":"United States"},
    "KLAC": {"name":"KLA Corporation", "sector":"Technology", "industry":"Semiconductor Equipment & Materials", "theme":"Semiconductors", "region":"United States"},
    "ASML": {"name":"ASML Holding", "sector":"Technology", "industry":"Semiconductor Equipment & Materials", "theme":"Semiconductors", "region":"Europe"},
    "TSM": {"name":"Taiwan Semiconductor", "sector":"Technology", "industry":"Semiconductors", "theme":"Semiconductors", "region":"Taiwan"},
}

MARKETS = {
    "US": Market("United States", ""),
    "PL": Market("Poland", ".WA"),
    "UK": Market("United Kingdom", ".L"),
    "EU": Market("Europe", "multi"),
}


def _us_cap_range_screener(min_cap: float, max_cap: float, limit: int, sort_desc: bool = False) -> list[str]:
    """Generic Yahoo screener call for a US market-cap band. Yahoo's
    screener API caps each individual response at 250 rows, so reaching
    a higher `limit` means paginating with `offset` rather than asking
    for a bigger `size` in one call."""
    tickers: list[str] = []
    try:
        q = yf.EquityQuery(
            "and",
            [
                yf.EquityQuery("eq", ["region", "us"]),
                yf.EquityQuery("btwn", ["intradaymarketcap", min_cap, max_cap]),
                yf.EquityQuery("gt", ["dayvolume", 100_000]),
            ],
        )
        offset = 0
        page_size = 250
        while len(tickers) < limit:
            result = yf.screen(q, sortField="intradaymarketcap", sortAsc=not sort_desc, size=page_size, offset=offset)
            quotes = result.get("quotes", [])
            if not quotes:
                break
            tickers.extend(qq["symbol"] for qq in quotes if "symbol" in qq)
            offset += page_size
            if len(quotes) < page_size:
                break
        return tickers[:limit]
    except Exception as e:
        log.warning("US screener failed for range %s-%s (%s) — returning %d tickers fetched before failure", min_cap, max_cap, e, len(tickers))
        return tickers


def us_small_micro_cap(limit: int = 500) -> list[str]:
    """Small/micro-cap US equities ($50M-$2B)."""
    tickers = _us_cap_range_screener(50_000_000, 2_000_000_000, limit)
    log.info("US small/micro-cap screener returned %d tickers", len(tickers))
    return tickers


def us_mid_large_cap(limit: int = 500) -> list[str]:
    """Mid/large-cap US equities ($2B-$750B) not necessarily in the S&P
    500 — added because a real portfolio (dividend-focused especially)
    routinely holds mid-caps, REITs and BDCs that never make the index
    (e.g. AGNC, ADC, GAIN, CTRE) but are far too large for the
    small/micro-cap screener above."""
    tickers = _us_cap_range_screener(2_000_000_000, 750_000_000_000, limit, sort_desc=True)
    log.info("US mid/large-cap screener returned %d tickers", len(tickers))
    return tickers


def _wikipedia_table(url: str, match: str, symbol_col_candidates: list[str]) -> list[str]:
    """Fetches every table on the page (no upfront regex filter — Wikipedia's
    table headers/captions vary and shift over time, and a `match=` filter
    that misses just means an empty, un-diagnosable result) and scans each
    one for a column matching `symbol_col_candidates`. `match` is kept only
    as a logging hint, not a hard filter."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        log.info("Wikipedia GET %s -> HTTP %d, %d bytes", url, resp.status_code, len(resp.content))
        resp.raise_for_status()
        tables = pd.read_html(StringIO(resp.text))
        log.info("%s: pd.read_html found %d table(s) total (hint pattern was %r)", url, len(tables), match)

        for idx, df in enumerate(tables):
            cols = [str(c) for c in df.columns]
            col = next((c for c in df.columns if str(c) in symbol_col_candidates), None)
            if col is not None:
                vals = [str(s).strip() for s in df[col].dropna().tolist()]
                log.info("%s: table[%d] columns=%s -> matched column %r, %d symbols, e.g. %s",
                          url, idx, cols, col, len(vals), vals[:5])
                if vals:
                    return vals
            else:
                log.info("%s: table[%d] columns=%s -> no match", url, idx, cols)

        log.warning("No table on %s had a column matching %s", url, symbol_col_candidates)
        return []
    except Exception as e:
        log.warning("Wikipedia fetch failed for %s (%s: %s)", url, type(e).__name__, e)
        return []


def sp500_constituents() -> list[str]:
    """Large-cap coverage gap fix: the small/micro-cap screener above
    deliberately excludes anything over $2B market cap, but a real
    portfolio (which is the whole point of the CSV/JSON import feature)
    is likely to hold large-caps. S&P 500 constituents cover most of
    that gap for US equities at effectively zero extra engineering cost
    — same Wikipedia-table pattern as the AU/PL/UK legs."""
    raw = _wikipedia_table(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        match="Symbol",
        symbol_col_candidates=["Symbol", "Ticker symbol", "Ticker"],
    )
    # Wikipedia's Symbol column sometimes uses a dot for share classes
    # (e.g. "BRK.B") where Yahoo Finance expects a dash ("BRK-B").
    return [s.replace(".", "-") for s in raw]




def wig_constituents() -> list[str]:
    # DISABLED — not called from build_universe(). Both the English and
    # Polish Wikipedia WIG20 articles failed to yield a parseable
    # constituents table (confirmed via pipeline_log.txt on real runs:
    # the Polish page's tables lack proper <th> headers, so pandas
    # returns generic '0'/'1' column names). No verified, current,
    # free source for the 20 tickers was found. Left here undeleted in
    # case a working source turns up later — kept honest as "off",
    # not silently broken.
    raw = _wikipedia_table(
        "https://pl.wikipedia.org/wiki/WIG20",
        match="Ticker",
        symbol_col_candidates=["Ticker", "Symbol", "Skrót", "Kod"],
    )
    return [f"{s}.WA" for s in raw]


def ftse_constituents() -> list[str]:
    raw = _wikipedia_table(
        "https://en.wikipedia.org/wiki/FTSE_100_Index",
        match="Ticker",
        symbol_col_candidates=["Ticker", "EPIC"],
    )
    return [f"{s}.L" for s in raw]



def europe_constituents() -> list[str]:
    """Pragmatic European large-cap universe from major national indices."""
    specs = [
        ("https://en.wikipedia.org/wiki/DAX", ["Ticker", "Symbol"], ".DE"),
        ("https://en.wikipedia.org/wiki/CAC_40", ["Ticker", "Symbol"], ".PA"),
        ("https://en.wikipedia.org/wiki/AEX_index", ["Ticker", "Symbol"], ".AS"),
        ("https://en.wikipedia.org/wiki/IBEX_35", ["Ticker", "Symbol"], ".MC"),
        ("https://en.wikipedia.org/wiki/FTSE_MIB", ["Ticker", "Symbol"], ".MI"),
        ("https://en.wikipedia.org/wiki/Swiss_Market_Index", ["Ticker", "Symbol"], ".SW"),
    ]
    out=[]
    for url, cols, suffix in specs:
        raw=_wikipedia_table(url, match="Ticker", symbol_col_candidates=cols)
        out.extend(f"{x.split()[0].replace('.', '-').strip()}{suffix}" for x in raw if x)
        time.sleep(0.4)
    return sorted(set(out))



def extra_portfolio_tickers() -> list[str]:
    """Load optional extra Yahoo symbols from data/extra_tickers.json.

    The base universe is discovered from screeners/indices and is intentionally
    finite. A valid Yahoo ticker can therefore exist without being selected by
    those discovery sources. Keeping a small explicit extension list prevents
    real portfolio holdings from being incorrectly labelled as unknown while
    avoiding the cost of fetching fundamentals for every symbol on every
    exchange. Invalid/stale symbols simply fail later in fetch_many and are
    skipped by the normal pipeline safeguards.
    """
    path = os.path.join(os.path.dirname(__file__), "..", "data", "extra_tickers.json")
    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        values = payload.get("tickers", payload) if isinstance(payload, dict) else payload
        out = sorted({str(x).strip().upper() for x in values if str(x).strip()})
        log.info("Extra portfolio coverage: %d ticker(s) loaded", len(out))
        return out
    except FileNotFoundError:
        log.info("No data/extra_tickers.json found; continuing without explicit portfolio extension")
        return []
    except Exception as e:
        log.warning("Could not load extra_tickers.json (%s)", e)
        return []

def build_universe() -> dict[str, list[str]]:
    """Returns {market_code: [tickers]}. Each leg is independent — one
    source failing does not block the others."""
    universe = {
        "US": sorted(set(us_small_micro_cap()) | set(sp500_constituents()) | set(us_mid_large_cap())),
    }
    time.sleep(1)
    universe["UK"] = ftse_constituents()
    time.sleep(1)
    universe["EU"] = europe_constituents()
    universe["ETF"] = sorted(ETF_UNIVERSE.keys())  # v0.98: enrich the complete tracked ETF catalogue every run
    universe["DISCOVERY"] = sorted(STOCK_DISCOVERY_CATALOG)
    universe["EXTRA"] = extra_portfolio_tickers()

    for market, tickers in universe.items():
        log.info("%s: %d tickers", market, len(tickers))

    return universe


if __name__ == "__main__":
    u = build_universe()
    total = sum(len(v) for v in u.values())
    print(f"Total tickers across all markets: {total}")
