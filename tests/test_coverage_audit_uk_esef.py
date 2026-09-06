from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import coverage_audit


def _row(**overrides):
    row = {
        "ticker": "AZN.L",
        "region": "United Kingdom",
        "quote_type": "EQUITY",
        "data_sources": ["Yahoo Finance"],
        "roe": None,
        "roa": 0.1,
        "profit_margin": 0.2,
        "operating_margin": 0.2,
        "gross_margin": 0.5,
        "revenue_growth": 0.05,
        "earnings_growth": 0.05,
        "free_cash_flow": 1.0,
        "operating_cash_flow": 1.0,
        "current_ratio": 1.0,
        "quick_ratio": 1.0,
        "debt_to_equity": 1.0,
        "trailing_pe": 20.0,
        "forward_pe": 18.0,
        "price_to_book": 4.0,
        "enterprise_to_ebitda": 12.0,
        "roce_proxy": 0.15,
    }
    row.update(overrides)
    return row


def test_sparse_uk_equity_routes_to_official_uksef_before_yahoo_statement_gap():
    assert coverage_audit.retrieval_lane(_row()) == "esef"


def test_uk_equity_moves_past_esef_only_after_filing_source_is_present():
    row = _row(data_sources=["Yahoo Finance", "ESEF / filings.xbrl.org"])
    assert coverage_audit.retrieval_lane(row) == "annual_statement_gap"


if __name__ == "__main__":
    test_sparse_uk_equity_routes_to_official_uksef_before_yahoo_statement_gap()
    test_uk_equity_moves_past_esef_only_after_filing_source_is_present()
