from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RANKER = ROOT / "scripts" / "opportunity_rank.py"


def load_ranker():
    spec = importlib.util.spec_from_file_location("vestra_opportunity_rank", RANKER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def strong_row(**overrides):
    closes = [100.0] * 70
    # Keep an older high so the candidate has room below the 52w high while
    # retaining mildly positive 20d/60d momentum.
    closes[5] = 120.0
    for i in range(49, 70):
        closes[i] = 102.0 + (i - 49) * 0.35
    row = {
        "quote_type": "EQUITY",
        "score": 90,
        "confidence_score": 90,
        "data_coverage_pct": 90,
        "critical_metric_coverage_pct": 90,
        "score_reliability": "reliable",
        "risk_gate": "clear",
        "moat_score": 90,
        "capital_allocation_intelligence_score": 90,
        "qarp_score": 90,
        "value_trap_risk_score": 10,
        "sector_native_score": 90,
        "low52_opportunity_score": 80,
        "recovery_score": 90,
        "valuation_score": 90,
        "fair_value_upside_pct": 25,
        "margin_of_safety_pct": 15,
        "valuation_confidence": "high",
        "valuation_signal": "undervalued",
        "valuation_method_count": 3,
        "valuation_dispersion_pct": 20,
        "estimate_signal": "improving",
        "estimate_momentum_score": 80,
        "analyst_snapshot_age_days": 1,
        "analyst_coverage_pct": 80,
        "estimate_confidence": "high",
        "analyst_refresh_state": "fresh",
        "analyst_eps_revisions_up_30d": 4,
        "analyst_eps_revisions_down_30d": 0,
        "recovery_status": "confirmed",
        "thesis_direction": "up",
        "price_history_1y": [{"close": x} for x in closes],
    }
    row.update(overrides)
    return row


def test_strong_outflow_with_etf_confirmation_caps_at_59():
    m = load_ranker()
    out = m.assess(strong_row(
        opportunity_rotation_theme="Semicondutores",
        opportunity_rotation_signal="strong_outflow",
        opportunity_rotation_etf_confirmed=True,
    ))
    assert out["opportunity_score_raw"] > 59
    assert out["opportunity_score"] == 59.0
    assert any(cap["reason"] == "Rotação semanal fortemente desfavorável" and cap["cap"] == 59.0
               for cap in out["opportunity_caps"])


def test_strong_outflow_without_etf_confirmation_caps_at_64():
    m = load_ranker()
    out = m.assess(strong_row(
        opportunity_rotation_signal="strong_outflow",
        opportunity_rotation_etf_confirmed=None,
    ))
    assert out["opportunity_score_raw"] > 64
    assert out["opportunity_score"] == 64.0


def test_outflow_caps_depend_on_etf_confirmation():
    m = load_ranker()
    confirmed = m.assess(strong_row(
        opportunity_rotation_signal="outflow",
        opportunity_rotation_etf_confirmed=True,
    ))
    unconfirmed = m.assess(strong_row(
        opportunity_rotation_signal="outflow",
        opportunity_rotation_etf_confirmed=None,
    ))
    assert confirmed["opportunity_score"] == 64.0
    assert unconfirmed["opportunity_score"] == 69.0


def test_severe_adverse_market_regime_caps_at_59():
    m = load_ranker()
    out = m.assess(strong_row(opportunity_market_regime="severe_adverse"))
    assert out["opportunity_score_raw"] > 59
    assert out["opportunity_score"] == 59.0
    assert any(cap["reason"] == "Regime de mercado severamente adverso" and cap["cap"] == 59.0
               for cap in out["opportunity_caps"])


def test_favourable_rotation_explains_but_does_not_add_alpha():
    m = load_ranker()
    baseline = m.assess(strong_row())
    favourable = m.assess(strong_row(
        opportunity_rotation_theme="Semicondutores",
        opportunity_rotation_signal="strong_inflow",
        opportunity_market_regime="supportive",
    ))
    assert favourable["opportunity_score_raw"] == baseline["opportunity_score_raw"]
    assert favourable["opportunity_score"] == baseline["opportunity_score"]
    assert any("Rotação semanal favorável" in reason for reason in favourable["opportunity_reasons"])
    assert "Regime de mercado favorável" in favourable["opportunity_reasons"]
