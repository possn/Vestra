"""
run.py — pipeline entry point. Executed daily by GitHub Actions.

US screener -> intl index scrapes -> yfinance fundamentals -> scoring ->
SEC EDGAR insider activity (US only) -> data/stocks.json (committed to repo).

The PWA is a pure static consumer of data/stocks.json — it never calls
any external API directly, which is what keeps the whole thing free and
avoids CORS/rate-limit problems in the browser.
"""
from __future__ import annotations

import dataclasses
import datetime
import io
import json
import logging
import os
import sys
import traceback

from fundamentals import fetch_many
from sec_enrich import enrich as enrich_sec
from esef_enrich import enrich as enrich_esef
from capital_risk import enrich as enrich_capital_risk
from confidence import assess as assess_confidence
from valuation import assess as assess_valuation
from earnings_intelligence import assess as assess_earnings_intelligence
from catalysts import assess as assess_catalysts
from low52_intelligence import assess as assess_low52_intelligence
from peer_drawdown import assess_universe as assess_peer_drawdown
from recovery_confirmation import assess_universe as assess_recovery_confirmation
from drawdown_diagnosis import assess as assess_drawdown_diagnosis
from scanner import assess as assess_scanner
from analyst import fetch_many as fetch_analyst_many
import history as history_mod
import valuation_history as valuation_history_mod
from insiders import annotate as annotate_insiders
from insider_prices import fetch_many as fetch_insider_prices
from congress import fetch_congress_for_universe
from metals import build_metals_payload
from metals_brief import build_metals_brief
import metals_history as metals_history_mod
from fx import build_fx_payload
from fx_history import build_fx_history_payload
from news import fetch_news_for_universe
from score import score_universe
from thesis import classify as classify_thesis, evolve as evolve_thesis
import thesis_history as thesis_history_mod
from universe import build_universe, ETF_UNIVERSE, STOCK_DISCOVERY_CATALOG, region_for_equity
# v1.1 (auditoria): estes 6 módulos já existiam no repositório mas não eram
# chamados por ninguém — construídos, nunca ligados. gap_retrieval e
# quarterly_gap_retrieval dizem no seu próprio docstring quando devem correr
# (depois do enrich_esef; um depois do outro); os 4 "assess" são overlays
# que não substituem o score principal, adicionam contexto.
from gap_retrieval import enrich as enrich_gap_retrieval
from quarterly_gap_retrieval import enrich as enrich_quarterly_gap_retrieval
from derived_fundamentals import enrich as enrich_derived_fundamentals
from capital_allocation_intelligence import assess as assess_capital_allocation
from moat import assess as assess_moat
from sector_native import assess as assess_sector_native
from value_trap import assess as assess_value_trap

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "stocks.json")
METALS_OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "metals.json")
METALS_HISTORY_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "metals_history.json")
METALS_BRIEF_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "metals_brief.json")
FX_OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "fx.json")
FX_HISTORY_OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "fx_history.json")
HISTORY_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "history.json")
VALUATION_HISTORY_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "valuation_history.json")
THESIS_HISTORY_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "thesis_history.json")
NEWS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "news.json")
ERROR_LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "last_error.log")
PIPELINE_LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "pipeline_log.txt")
LEARNED_SNAPSHOT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "learned_tickers.json")

# Every run's log is captured to a string AND committed to the repo as
# data/pipeline_log.txt, in addition to going to stdout for the Actions
# UI. This is the primary debugging channel: GitHub Actions log storage
# is a temporary blob that expires and isn't reachable from every
# environment, but a file in the repo is reachable from anywhere with
# read access to the repo (including the plain REST contents API).
_log_buffer = io.StringIO()
_handler_stream = logging.StreamHandler(_log_buffer)
_handler_console = logging.StreamHandler(sys.stdout)
_fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
_handler_stream.setFormatter(_fmt)
_handler_console.setFormatter(_fmt)
logging.basicConfig(level=logging.WARNING, handlers=[_handler_stream, _handler_console], force=True)
for _name in ("run", "universe", "fundamentals", "sec_enrich", "esef_enrich", "derived_fundamentals", "capital_risk", "confidence", "analyst", "insiders", "insider_prices", "congress", "score", "thesis", "metals", "fx", "fx_history", "history", "valuation_history", "thesis_history", "news"):
    logging.getLogger(_name).setLevel(logging.INFO)
log = logging.getLogger("run")


def _flush_pipeline_log():
    try:
        os.makedirs(os.path.dirname(PIPELINE_LOG_PATH), exist_ok=True)
        with open(PIPELINE_LOG_PATH, "w") as f:
            f.write(_log_buffer.getvalue())
    except Exception:
        pass  # never let log-writing itself break the run

# Reference expense-ratio benchmarks by broad category, used only for the
# fee-audit "vs. category average" comparison. Figures are illustrative
# industry averages (ballpark, low single digits of a percent) roughly in
# line with published ICI Fact Book asset-weighted averages for US funds —
# NOT ticker-specific and NOT re-verified against a live source at run
# time. Treat the fee audit as directional, not authoritative; a user who
# needs an exact figure should check the fund's own prospectus.
CATEGORY_BENCHMARKS = {
    "index_equity": 0.0005,   # broad passive index funds/ETFs, ~5 bps
    "active_equity": 0.0066,  # actively managed equity funds, ~66 bps
    "sector_thematic": 0.0045,  # thematic/sector ETFs
    "bond": 0.0035,
}


def _json_safe(obj):
    """Recursively replaces NaN/Infinity floats with None. Python's json
    module happily writes the literal tokens NaN/Infinity by default
    (allow_nan=True) — those are NOT valid JSON per the spec, and
    browsers' JSON.parse rejects the entire file when it hits one. This
    is a last-line-of-defense sweep so a single bad float anywhere in
    the pipeline can't silently corrupt the whole stocks.json for every
    user, the way it did before this function existed."""
    if isinstance(obj, float):
        return obj if (obj == obj and obj not in (float("inf"), float("-inf"))) else None
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    return obj


def _load_learned_tickers() -> list[str]:
    """Return centrally validated search discoveries in stable snapshot order.

    These names must be fetched before the much larger portfolio/universe pools:
    otherwise a late Yahoo throttle can make a newly learned company disappear
    between extra_tickers.json and the scored catalogue even though its identity
    was already validated by the production Worker.
    """
    try:
        with open(LEARNED_SNAPSHOT_PATH, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        rows = payload.get("rows", []) if isinstance(payload, dict) else []
        out=[]
        seen=set()
        for row in rows:
            ticker = str((row or {}).get("ticker") or "").strip().upper() if isinstance(row, dict) else ""
            if ticker and ticker not in seen:
                seen.add(ticker); out.append(ticker)
        return out
    except Exception as exc:
        log.warning("Could not load learned ticker snapshot: %s", exc)
        return []


def main():
    # Preserve previously enriched ETF catalogue rows. The wider fund universe is
    # refreshed in rotation, so a name not fetched today should keep yesterday's
    # observed TER/AUM/holdings rather than falling back to metadata-only.
    previous_etfs = {}
    previous_equities = {}
    try:
        if os.path.exists(OUT_PATH):
            with open(OUT_PATH, "r", encoding="utf-8") as _f:
                _prev = json.load(_f)
            _prev_rows = _prev.get("stocks") or []
            previous_etfs = {
                str(r.get("ticker") or ""): r
                for r in _prev_rows
                if r.get("quote_type") == "ETF" and r.get("ticker")
            }
            previous_equities = {
                str(r.get("ticker") or ""): r
                for r in _prev_rows
                if r.get("quote_type") != "ETF" and r.get("ticker")
            }
    except Exception as exc:
        log.warning("Could not load previous catalogue: %s", exc)
        previous_etfs = {}
        previous_equities = {}

    universe = build_universe()
    all_tickers = sorted({t for tickers in universe.values() for t in tickers})
    portfolio_tickers = list(dict.fromkeys(universe.get("EXTRA", [])))
    portfolio_set = set(portfolio_tickers)
    learned_tickers = [t for t in _load_learned_tickers() if t in portfolio_set]
    learned_set = set(learned_tickers)
    portfolio_remainder = [t for t in portfolio_tickers if t not in learned_set]
    remainder_tickers = [t for t in all_tickers if t not in portfolio_set]
    log.info(
        "Total universe: %d tickers (%d learned-priority, %d other portfolio-priority)",
        len(all_tickers), len(learned_tickers), len(portfolio_remainder),
    )

    if not all_tickers:
        log.error("Empty universe — aborting without overwriting existing data/stocks.json")
        return

    # Search-discovered names are fetched first in a tiny isolated pool. They are
    # new to the canonical catalogue and have no previous scored row to fall back
    # to, so letting them sit near the end of a 400+ ticker portfolio batch makes
    # them disproportionately vulnerable to a late Yahoo rate-limit.
    raw_learned = fetch_many(learned_tickers, workers_override=1, retries=3, pause=0.10)

    # Fetch the user's remaining holdings next, then the broad universe.
    raw_portfolio = fetch_many(portfolio_remainder, workers_override=3, retries=2, pause=0.05)
    raw_remainder = fetch_many(remainder_tickers, retries=1)
    raw_by_symbol = {r.ticker: r for r in raw_remainder}
    raw_by_symbol.update({r.ticker: r for r in raw_portfolio})
    raw_by_symbol.update({r.ticker: r for r in raw_learned})
    raw = [raw_by_symbol[t] for t in all_tickers if t in raw_by_symbol]
    raw = enrich_sec(raw, priority=portfolio_set)
    raw = enrich_esef(raw, priority=portfolio_set)
    raw = enrich_gap_retrieval(raw, priority=portfolio_set)
    raw = enrich_quarterly_gap_retrieval(raw, priority=portfolio_set)
    raw = enrich_derived_fundamentals(raw)
    raw = enrich_capital_risk(raw, priority=portfolio_set)
    scored = score_universe(raw)
    scored_now = {s.ticker for s in scored}
    missing_learned = [t for t in learned_tickers if t not in scored_now]
    if missing_learned:
        details = {
            t: getattr(raw_by_symbol.get(t), "error", None) or "not scoreable from fetched metrics"
            for t in missing_learned
        }
        log.error("Learned ticker promotion incomplete: %s", details)
    elif learned_tickers:
        log.info("Learned ticker promotion complete: %s", ", ".join(learned_tickers))

    analyst_map = fetch_analyst_many(
        [dataclasses.asdict(s) for s in scored],
        priority_tickers=set(universe.get("EXTRA", [])),
    )

    us_tickers = [s.ticker for s in scored if "." not in s.ticker and s.quote_type != "ETF"]
    insider_map = annotate_insiders(us_tickers)
    congress_map = fetch_congress_for_universe(us_tickers)
    # v0.97: price history is dossier infrastructure, not only an insider helper.
    # Fetch weekly 1y histories in Yahoo batches for the live universe + complete ETF catalogue.
    price_history_tickers = sorted(set(all_tickers) | set(ETF_UNIVERSE.keys()))
    insider_price_map = fetch_insider_prices(price_history_tickers)
    raw_by_ticker = {r.ticker: r for r in raw}
    today = datetime.date.today().isoformat()
    thesis_history = thesis_history_mod.load(THESIS_HISTORY_PATH)

    rows = []
    scored_symbols = {s.ticker for s in scored}
    for s in scored:
        row = dataclasses.asdict(s)
        if row.get("quote_type") == "ETF":
            etf_meta = ETF_UNIVERSE.get(s.ticker, {})
            if not row.get("sector"):
                row["sector"] = etf_meta.get("sector")
            row["region"] = etf_meta.get("region", "Global")
            row["fund_region"] = etf_meta.get("region", row.get("region", "Global"))
            row["fund_theme"] = etf_meta.get("theme") or row.get("fund_theme")
            row["fund_style"] = etf_meta.get("style") or row.get("fund_style")
            if etf_meta.get("ucits"):
                row["fund_ucits"] = etf_meta.get("ucits")
        elif row.get("quote_type") == "CRYPTO":
            row["region"] = "Global"
        else:
            row["region"] = region_for_equity(s.ticker)
        analyst = analyst_map.get(s.ticker)
        if analyst:
            for key, value in analyst.items():
                if key != "ticker":
                    row[f"analyst_{key}"] = value
        else:
            row["analyst_status"] = "not_requested"
            row["analyst_coverage_pct"] = 0.0

        insider = insider_map.get(s.ticker, {"status": "not_available"})
        row["insider_status"] = insider.get("status", "not_available")
        row["insider_form4_count_30d"] = insider.get("form4_count_30d", "not_available")
        row["insider_buy_count_30d"] = insider.get("buy_count_30d")
        row["insider_sell_count_30d"] = insider.get("sell_count_30d")
        row["insider_buy_value_30d"] = insider.get("buy_value_30d")
        row["insider_sell_value_30d"] = insider.get("sell_value_30d")
        row["insider_net_value_30d"] = insider.get("net_value_30d")
        row["insider_transactions"] = insider.get("transactions", [])
        row["congress_trades"] = congress_map.get(s.ticker, [])
        row["insider_form4_count_365d"] = insider.get("form4_count_365d")
        row["insider_buy_count_365d"] = insider.get("buy_count_365d")
        row["insider_sell_count_365d"] = insider.get("sell_count_365d")
        row["insider_buy_value_365d"] = insider.get("buy_value_365d")
        row["insider_sell_value_365d"] = insider.get("sell_value_365d")
        row["insider_net_value_365d"] = insider.get("net_value_365d")
        row["insider_transactions_365d"] = insider.get("transactions_365d", [])
        _hist = insider_price_map.get(s.ticker) or (previous_etfs.get(s.ticker, {}) if row.get("quote_type") == "ETF" else previous_equities.get(s.ticker, {})).get("price_history_1y") or []
        row["price_history_1y"] = _hist
        # Removed the "insider_price_history_1y" duplicate alias that used
        # to sit here (identical data, ~4MB of pure waste across the whole
        # file). All frontend call sites now read price_history_1y only.
        if row.get("current_price") is None and _hist:
            row["current_price"] = _hist[-1].get("close")
        if row.get("quote_type") == "ETF" and len(_hist) >= 2:
            try:
                _a=float(_hist[0].get("close")); _b=float(_hist[-1].get("close"))
                row["fund_return_1y_pct"] = round((_b/_a-1)*100, 2) if _a else None
            except Exception:
                row["fund_return_1y_pct"] = None
        row["insider_reason"] = insider.get("reason")
        row["insider_detail_filings_parsed"] = insider.get("detail_filings_parsed")

        rm = raw_by_ticker.get(s.ticker)
        row["data_sources"] = ["Yahoo Finance"]
        _derived_metrics = list(getattr(rm, "derived_metrics", []) or []) if rm is not None else []
        if _derived_metrics:
            row["derived_metrics"] = _derived_metrics
            row["derived_metric_note"] = "Calculated only from observed inputs; never an independent source"
        if rm is not None and getattr(rm, "sec_edgar_enriched", False):
            row["data_sources"].append("SEC EDGAR")
            row["sec_period_end"] = getattr(rm, "sec_period_end", None)
            row["source_agreement_checks"] = getattr(rm, "source_agreement_checks", 0)
            row["source_agreement_pct"] = getattr(rm, "source_agreement_pct", None)
        if rm is not None and getattr(rm, "esef_enriched", False):
            row["data_sources"].append("ESEF / filings.xbrl.org")
            row["identity_source"] = "GLEIF/ANNA ISIN→LEI"
            row["isin"] = getattr(rm, "isin", None)
            row["lei"] = getattr(rm, "lei", None)
            row["esef_period_end"] = getattr(rm, "esef_period_end", None)
        if rm is not None and getattr(rm, "gap_statement_enriched", False):
            row["data_sources"].append("Yahoo Statements (targeted)")
            row["gap_statement_enriched"] = True
            row["gap_coverage_before"] = getattr(rm, "gap_coverage_before", None)
            row["gap_coverage_after"] = getattr(rm, "gap_coverage_after", None)
        if rm is not None and getattr(rm, "quarterly_gap_enriched", False):
            row["data_sources"].append("Yahoo Quarterly Statements (TTM)")
            row["quarterly_gap_enriched"] = True
            row["quarterly_gap_coverage_before"] = getattr(rm, "quarterly_gap_coverage_before", None)
            row["quarterly_gap_coverage_after"] = getattr(rm, "quarterly_gap_coverage_after", None)
        if analyst: row["data_sources"].append("Analyst feed")
        if insider.get("status") not in (None,"not_available","error"): row["data_sources"].append("SEC Form 4")
        if row.get("congress_trades"): row["data_sources"].append("U.S. House Clerk / STOCK Act")
        if rm is not None:
            if getattr(rm, "capital_risk_checked", False):
                row["data_sources"].append("SEC Capital Structure")
                row["capital_structure_flags"] = getattr(rm, "capital_structure_flags", [])
                row["capital_structure_risk"] = getattr(rm, "capital_structure_risk", "clear")
                row["reverse_split_count_24m"] = getattr(rm, "reverse_split_count_24m", 0)
                row["reverse_split_latest_date"] = getattr(rm, "reverse_split_latest_date", None)
                row["capital_risk_filings_checked"] = getattr(rm, "capital_risk_filings_checked", 0)
            if row.get("quote_type") == "ETF":
                row["top_holdings"] = rm.top_holdings
                row["fund_family"] = rm.fund_family
                row["fund_category"] = rm.fund_category
                row["fund_legal_type"] = rm.fund_legal_type
                row["fund_inception_date"] = rm.fund_inception_date
                row["fund_description"] = rm.fund_description
                row["fund_total_assets"] = rm.fund_total_assets
                row["fund_asset_classes"] = rm.fund_asset_classes
                row["fund_sector_weightings"] = rm.fund_sector_weightings
            row["quarterly_revenue"] = rm.quarterly_revenue
            row["quarterly_net_income"] = rm.quarterly_net_income
            row["quarterly_diluted_shares"] = rm.quarterly_diluted_shares
            row["quarterly_eps"] = rm.quarterly_eps
            row["quarterly_rnd"] = rm.quarterly_rnd
            row["eps_yoy_latest"] = rm.eps_yoy_latest
            row["eps_yoy_prior"] = rm.eps_yoy_prior
            row["eps_yoy_acceleration_pp"] = rm.eps_yoy_acceleration_pp
            row["rnd_latest_quarter"] = rm.rnd_latest_quarter
            row["rnd_yoy"] = rm.rnd_yoy
            row["rnd_to_revenue"] = rm.rnd_to_revenue
            row["roce_proxy"] = rm.roce_proxy
            row["dividend_fcf_coverage"] = rm.dividend_fcf_coverage
            row["annual_quality_history"] = rm.annual_quality_history
            row["annual_dividend_history"] = rm.annual_dividend_history
            row["revenue_yoy_latest"] = rm.revenue_yoy_latest
            row["revenue_yoy_prior"] = rm.revenue_yoy_prior
            row["revenue_yoy_acceleration_pp"] = rm.revenue_yoy_acceleration_pp
            row["net_income_yoy_latest"] = rm.net_income_yoy_latest
            row["net_income_yoy_prior"] = rm.net_income_yoy_prior
            row["net_income_yoy_acceleration_pp"] = rm.net_income_yoy_acceleration_pp
            row["diluted_shares_yoy"] = rm.diluted_shares_yoy
            row["net_margin_latest"] = rm.net_margin_latest
            row["net_margin_yoy_change_pp"] = rm.net_margin_yoy_change_pp
            row["net_margin_yoy_change_prior_pp"] = rm.net_margin_yoy_change_prior_pp
            row["repurchases_last_quarter"] = rm.repurchases_last_quarter
        row.update(assess_earnings_intelligence(row))
        row.update(assess_confidence(row))
        row.update(assess_valuation(row))
        row.update(assess_capital_allocation(row))
        row.update(assess_moat(row))
        row.update(assess_sector_native(row))
        row.update(assess_value_trap(row))
        row.update(classify_thesis(row))
        prev_date, prev_snapshot = thesis_history_mod.previous(thesis_history, s.ticker, today)
        d7_date, d7_snapshot = thesis_history_mod.nearest_days_ago(thesis_history, s.ticker, today, 7)
        d30_date, d30_snapshot = thesis_history_mod.nearest_days_ago(thesis_history, s.ticker, today, 30)
        row.update(evolve_thesis(
            row, prev_snapshot, prev_date,
            d7_snapshot, d7_date, d30_snapshot, d30_date,
        ))
        row.update(assess_catalysts(row))
        row.update(assess_low52_intelligence(row))
        row.update(assess_drawdown_diagnosis(row))
        row.update(assess_scanner(row))
        rows.append(row)

    portfolio_extra = set(universe.get("EXTRA", []))
    row_tickers = {r.get("ticker") for r in rows}
    portfolio_covered = len(portfolio_extra & row_tickers)
    etf_rows = [r for r in rows if r.get("quote_type") == "ETF"]
    etf_holdings_rows = sum(1 for r in etf_rows if r.get("top_holdings"))
    us_equity_rows = [r for r in rows if r.get("quote_type") != "ETF" and "." not in (r.get("ticker") or "")]
    insider_ok_rows = sum(1 for r in us_equity_rows if r.get("insider_status") == "ok")
    insider_degraded_rows = sum(1 for r in us_equity_rows if r.get("insider_status") == "degraded")
    # "degraded" means SEC submissions were reached but one or more Form 4 detail
    # documents could not be parsed. It is still a successfully checked issuer and
    # must not be confused with SEC being unavailable/no CIK mapping.
    insider_checked_rows = insider_ok_rows + insider_degraded_rows
    insider_rows_with_form4 = sum(1 for r in us_equity_rows if isinstance(r.get("insider_form4_count_30d"), int) and r.get("insider_form4_count_30d", 0) > 0)
    insider_rows_with_ps = sum(1 for r in us_equity_rows if (r.get("insider_buy_count_30d") or 0) + (r.get("insider_sell_count_30d") or 0) > 0)

    analyst_requested = len(analyst_map)
    analyst_ok = sum(1 for a in analyst_map.values() if a.get("status") == "ok")
    analyst_partial = sum(1 for a in analyst_map.values() if a.get("status") == "partial")
    analyst_with_revisions = sum(1 for a in analyst_map.values() if a.get("eps_next_q_revision_30d_pct") is not None or a.get("eps_next_y_revision_30d_pct") is not None)
    analyst_with_surprise = sum(1 for a in analyst_map.values() if a.get("latest_eps_surprise_pct") is not None)
    analyst_with_next_earnings = sum(1 for a in analyst_map.values() if a.get("next_earnings_date"))
    analyst_earnings_within_14d = sum(1 for a in analyst_map.values() if isinstance(a.get("days_to_earnings"), int) and 0 <= a.get("days_to_earnings") <= 14)

    # Keep the equity discovery universe stable across transient Yahoo failures.
    # A ticker that was successfully enriched on a previous run should not
    # disappear merely because today's quote/fundamental request was throttled.
    present_equities = {str(r.get("ticker") or "") for r in rows if r.get("quote_type") != "ETF"}
    current_equity_universe = set().union(*(set(universe.get(k, [])) for k in ("US", "UK", "EU", "PL", "DISCOVERY", "EXTRA")))
    for ticker in sorted(current_equity_universe):
        if ticker in present_equities or ticker in ETF_UNIVERSE:
            continue
        meta = STOCK_DISCOVERY_CATALOG.get(ticker, {})
        previous = previous_equities.get(ticker)
        if previous:
            carried = dict(previous)
            carried["name"] = meta.get("name") or carried.get("name") or ticker
            carried["sector"] = meta.get("sector") or carried.get("sector")
            carried["industry"] = meta.get("industry") or carried.get("industry")
            carried["stock_theme"] = meta.get("theme") or carried.get("stock_theme")
            carried["region"] = meta.get("region") or carried.get("region") or region_for_equity(ticker)
            carried["pipeline_status"] = "equity_carried_forward"
            rows.append(carried)
            continue
        if meta:
            rows.append({
                "ticker": ticker,
                "name": meta.get("name") or ticker,
                "sector": meta.get("sector"),
                "industry": meta.get("industry"),
                "stock_theme": meta.get("theme"),
                "region": meta.get("region") or region_for_equity(ticker),
                "quote_type": "EQUITY",
                "score": None,
                "quality_pct": None,
                "growth_pct": None,
                "value_pct": None,
                "data_confidence": "metadata_only",
                "data_coverage_pct": 0,
                "pipeline_status": "equity_catalog_only",
            })

    # Keep the curated ETF discovery universe visible even when Yahoo fails to
    # return full fundamentals for a ticker on a given run. These placeholder
    # rows are deliberately metadata-only: no fake price, TER, AUM or holdings.
    # The UI can discover/filter them, while Fee Saver/overlap only use rows
    # with real observed data.
    present = {str(r.get("ticker") or "") for r in rows}
    for ticker, meta in ETF_UNIVERSE.items():
        if ticker in present:
            continue
        previous = previous_etfs.get(ticker)
        if previous:
            carried = dict(previous)
            # Catalogue metadata is authoritative for discovery labels; observed
            # market/fund fields remain whatever Yahoo last returned.
            carried["sector"] = meta.get("sector") or carried.get("sector")
            carried["industry"] = meta.get("sector") or carried.get("industry")
            carried["region"] = meta.get("region", carried.get("region", "Global"))
            carried["fund_region"] = meta.get("region", carried.get("fund_region", "Global"))
            carried["fund_theme"] = meta.get("theme") or carried.get("fund_theme")
            carried["fund_style"] = meta.get("style") or carried.get("fund_style")
            carried["fund_category"] = meta.get("sector") or carried.get("fund_category")
            if meta.get("ucits"):
                carried["fund_ucits"] = meta.get("ucits")
            _hist = insider_price_map.get(ticker) or carried.get("price_history_1y") or carried.get("insider_price_history_1y") or []
            carried["price_history_1y"] = _hist
            carried.pop("insider_price_history_1y", None)
            if carried.get("current_price") is None and _hist:
                carried["current_price"] = _hist[-1].get("close")
            if len(_hist) >= 2:
                try:
                    _a=float(_hist[0].get("close")); _b=float(_hist[-1].get("close"))
                    carried["fund_return_1y_pct"] = round((_b/_a-1)*100, 2) if _a else None
                except Exception:
                    pass
            carried["pipeline_status"] = "catalog_carried_forward"
            rows.append(carried)
            continue
        rows.append({
            "ticker": ticker,
            "name": meta.get("name") or ticker,
            "sector": meta.get("sector"),
            "industry": meta.get("sector"),
            "market_cap": None,
            "currency": None,
            "quote_type": "ETF",
            "score": None,
            "data_confidence": "metadata_only",
            "data_coverage_pct": 0,
            "expense_ratio": None,
            "fund_total_assets": None,
            "top_holdings": [],
            "region": meta.get("region", "Global"),
            "fund_region": meta.get("region", "Global"),
            "fund_theme": meta.get("theme"),
            "fund_style": meta.get("style"),
            "fund_category": meta.get("sector"),
            "fund_ucits": meta.get("ucits"),
            "price_history_1y": insider_price_map.get(ticker, []),
            "fund_return_1y_pct": (round((insider_price_map[ticker][-1]["close"] / insider_price_map[ticker][0]["close"] - 1) * 100, 2) if len(insider_price_map.get(ticker, [])) >= 2 and insider_price_map[ticker][0].get("close") else None),
            "current_price": (insider_price_map[ticker][-1].get("close") if insider_price_map.get(ticker) else None),
            "pipeline_status": "catalog_only",
        })

    rows = assess_peer_drawdown(rows)
    rows = assess_recovery_confirmation(rows)

    payload = {
        "schema_version": 521,
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "data_quality": {
            "portfolio_extra_requested": len(portfolio_extra),
            "portfolio_extra_covered": portfolio_covered,
            "portfolio_extra_coverage_pct": round((portfolio_covered / len(portfolio_extra) * 100), 1) if portfolio_extra else 100.0,
            "etf_rows": len(etf_rows),
            "etf_catalog_total": len(ETF_UNIVERSE),
            "etf_rows_with_holdings": etf_holdings_rows,
            "insider_us_equities": len(us_equity_rows),
            "insider_sec_ok": insider_ok_rows,
            "insider_sec_degraded": insider_degraded_rows,
            "insider_sec_checked": insider_checked_rows,
            "insider_sec_checked_coverage_pct": round((insider_checked_rows / len(us_equity_rows) * 100), 1) if us_equity_rows else 100.0,
            "insider_rows_with_form4_30d": insider_rows_with_form4,
            "insider_rows_with_open_market_ps_30d": insider_rows_with_ps,
            "insider_sec_coverage_pct": round((insider_ok_rows / len(us_equity_rows) * 100), 1) if us_equity_rows else 100.0,
            "analyst_rows_requested": analyst_requested,
            "analyst_rows_ok": analyst_ok,
            "analyst_rows_partial": analyst_partial,
            "analyst_rows_with_revisions": analyst_with_revisions,
            "analyst_rows_with_surprise": analyst_with_surprise,
            "analyst_rows_with_next_earnings": analyst_with_next_earnings,
            "analyst_earnings_within_14d": analyst_earnings_within_14d,
            "analyst_coverage_pct": round(((analyst_ok + analyst_partial) / analyst_requested * 100), 1) if analyst_requested else 0.0,
        },
        "universe_counts": {k: len(v) for k, v in universe.items()},
        "category_benchmarks": CATEGORY_BENCHMARKS,
        "methodology_note": (
            "Composite score is an unvalidated, explainable multi-factor blend of public "
            "fundamentals. The factor mix is sector-aware: general companies, banks, REITs "
            "and insurers use distinct score packs. The REIT pack now uses statement-derived "
            "FFO/P-FFO/payout and leverage proxies while explicitly keeping AFFO, NAV and occupancy "
            "unavailable when specialist source data are absent. Other specialist packs omit "
            "industry-native metrics that are not yet available rather than fabricating them. "
            "Valuation context compares positive multiples with same-sector medians and also "
            "accumulates the scanner's own daily valuation observations over time. "
            "Not investment advice. See scripts/score.py for the exact "
            "formula and scripts/insiders.py + scripts/fundamentals.py "
            "for documented data limitations. The thesis taxonomy is deterministic and "
            "explainable (scripts/thesis.py), not a recommendation or forecast. Insider P/S signals are limited to "
            "open-market Form 4 transaction codes and quarterly growth/dilution and acceleration "
            "use up to the latest six Yahoo Finance quarters when available. Analyst estimates, "
            "EPS/revenue revisions, earnings surprises, recommendation counts and price targets are "
            "contextual evidence only and are not included in the core Finscanner score because "
            "coverage is uneven across markets. Upcoming earnings dates and recent beat/miss history are "
            "presented as catalyst/event-risk context and do not alter the core score."
        ),
        "stocks": rows,
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(_json_safe(payload), f, separators=(",", ":"))

    log.info("Wrote %d rows to %s", len(rows), OUT_PATH)

    metals_payload = build_metals_payload()
    metals_history = metals_history_mod.load(METALS_HISTORY_PATH)
    metals_history = metals_history_mod.update(metals_history, metals_payload, today)
    metals_payload = metals_history_mod.enrich(metals_payload, metals_history)
    metals_history_mod.save(metals_history, METALS_HISTORY_PATH)
    with open(METALS_OUT_PATH, "w") as f:
        json.dump(_json_safe(metals_payload), f, separators=(",", ":"))
    log.info("Wrote metals data to %s", METALS_OUT_PATH)

    metals_brief = build_metals_brief(metals_payload)
    with open(METALS_BRIEF_PATH, "w") as f:
        json.dump(_json_safe(metals_brief), f, separators=(",", ":"))
    log.info("Wrote daily metals brief to %s", METALS_BRIEF_PATH)

    previous_fx = None
    try:
        if os.path.exists(FX_OUT_PATH):
            with open(FX_OUT_PATH, "r", encoding="utf-8") as f:
                previous_fx = json.load(f)
    except Exception:
        previous_fx = None
    fx_payload = build_fx_payload(previous=previous_fx)
    with open(FX_OUT_PATH, "w") as f:
        json.dump(_json_safe(fx_payload), f, separators=(",", ":"))

    previous_fx_history = None
    try:
        if os.path.exists(FX_HISTORY_OUT_PATH):
            with open(FX_HISTORY_OUT_PATH) as f:
                previous_fx_history = json.load(f)
    except Exception:
        previous_fx_history = None
    fx_history_payload = build_fx_history_payload(previous=previous_fx_history)
    with open(FX_HISTORY_OUT_PATH, "w") as f:
        json.dump(_json_safe(fx_history_payload), f, separators=(",", ":"))
    log.info("Wrote FX data to %s", FX_OUT_PATH)

    history = history_mod.load(HISTORY_PATH)
    history = history_mod.update(history, rows, today)
    history_mod.save(history, HISTORY_PATH)

    valuation_history = valuation_history_mod.load(VALUATION_HISTORY_PATH)
    valuation_history = valuation_history_mod.update(valuation_history, rows, today)
    valuation_history_mod.save(valuation_history, VALUATION_HISTORY_PATH)

    thesis_history = thesis_history_mod.update(thesis_history, rows, today)
    thesis_history_mod.save(thesis_history, THESIS_HISTORY_PATH)

    news_payload = fetch_news_for_universe(all_tickers, {str(r.get("ticker") or ""): str(r.get("name") or "") for r in rows})
    with open(NEWS_PATH, "w") as f:
        json.dump(_json_safe(news_payload), f, separators=(",", ":"))
    log.info("Wrote news for %d tickers to %s", len(news_payload["tickers"]), NEWS_PATH)


if __name__ == "__main__":
    try:
        main()
        # Clear any stale error log from a previous failed run so success
        # is unambiguous in the repo state.
        if os.path.exists(ERROR_LOG_PATH):
            os.remove(ERROR_LOG_PATH)
        _flush_pipeline_log()
    except Exception:
        os.makedirs(os.path.dirname(ERROR_LOG_PATH), exist_ok=True)
        with open(ERROR_LOG_PATH, "w") as f:
            f.write(f"Failed at {datetime.datetime.utcnow().isoformat()}Z\n\n")
            f.write(traceback.format_exc())
        traceback.print_exc()
        _flush_pipeline_log()
        sys.exit(1)
