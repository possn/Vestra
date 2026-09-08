from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_etf_score_is_separate_from_equity_score_contract():
    src = (ROOT / "market-etf-intelligence.js").read_text(encoding="utf-8")
    assert "etf_score_model: 'etf_v1'" in src
    assert "etf_score:" in src
    assert "row.score" not in src
    assert "Recent performance" not in src  # performance is intentionally not a dominant labelled component
    assert "['cost', expenseScore(row), 0.25]" in src
    assert "['diversification', diversificationScore(row), 0.20]" in src
    assert "['risk', riskScore(row), 0.15]" in src


def test_market_loader_enriches_before_first_render():
    src = (ROOT / "market-static-universe.js").read_text(encoding="utf-8")
    enrich = src.index("window.VestraEtfIntelligence?.enrichStocks(stocks)")
    ready = src.index("beforeReady();")
    render = src.index("onReady();")
    assert enrich < ready < render
    assert "market-etf-intelligence.js?v=1.0" in src


def test_fund_rows_use_etf_score_and_show_pending_coverage():
    src = (ROOT / "market-row-ui.js").read_text(encoding="utf-8")
    assert "fund ? s?.etf_score : s?.score" in src
    assert "Por avaliar" in src
    assert "etf_score_coverage_pct" in src
    assert "q === 'FUND'" in src


def test_etf_module_is_in_pwa_bootstrap_without_cache_contract_bump():
    src = (ROOT / "sw.js").read_text(encoding="utf-8")
    assert '"./market-etf-intelligence.js"' in src
    assert '"market-etf-intelligence.js"' in src
    assert 'const CACHE_NAME = "vestra-cache-v128";' in src
    assert "Vestra Service Worker v10.14" in src
