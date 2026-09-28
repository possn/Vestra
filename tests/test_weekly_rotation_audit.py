from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "weekly_rotation_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("weekly_rotation_audit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def row(ticker, name, industry, r5, r20=0):
    return {
        "ticker": ticker,
        "name": name,
        "industry": industry,
        "quote_type": "EQUITY",
        "market_return_5d_pct": r5,
        "market_return_20d_pct": r20,
    }


def test_audit_matches_frontend_theme_contract_and_readiness():
    m = load_module()
    stocks = [
        row("S1", "Chip One", "Semiconductors", 2.0, 5.0),
        row("S2", "Chip Two", "Semiconductors", 1.0, 4.0),
        row("S3", "Chip Three", "Semiconductors", 3.0, 6.0),
        row("S4", "Chip Four", "Semiconductors", -1.0, 2.0),
        row("B1", "Bank One", "Banks", -3.0, -5.0),
        row("B2", "Bank Two", "Banks", -2.0, -4.0),
        row("B3", "Bank Three", "Banks", -1.0, -3.0),
        row("B4", "Bank Four", "Banks", 1.0, -2.0),
    ]
    payload = {"generated_at": "2026-09-28T00:00:00Z", "stocks": stocks}
    audit = m.build_audit(payload)
    assert audit["coverage"]["total"] == 10
    assert audit["coverage"]["ready"] == 2
    assert "Semicondutores" in audit["groups"]["inflows"]
    assert "Bancos" in audit["groups"]["outflows"]


def test_audit_decodes_actual_startup_layout_shape():
    m = load_module()
    packed = {
        "generated_at": "2026-09-28T00:00:00Z",
        "layout": "field_rows_v1",
        "fields": ["ticker", "name", "industry", "quote_type", "market_return_5d_pct"],
        "rows": [
            ["S1", "Chip One", "Semiconductors", "EQUITY", 1],
            ["S2", "Chip Two", "Semiconductors", "EQUITY", 1],
            ["S3", "Chip Three", "Semiconductors", "EQUITY", 1],
            ["S4", "Chip Four", "Semiconductors", "EQUITY", 1],
        ],
    }
    audit = m.build_audit(packed)
    semi = next(r for r in audit["themes"] if r["label"] == "Semicondutores")
    assert semi["weekly"] == 4
    assert semi["ready"] is True


def test_fund_detection_mirrors_frontend_contract():
    m = load_module()
    assert m.is_fund({"quote_type": "ETF", "name": "Something"})
    assert m.is_fund({"quote_type": "EQUITY", "name": "iShares Example"})
    assert not m.is_fund({"quote_type": "EQUITY", "name": "Example Corp"})
