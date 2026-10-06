from pathlib import Path
import importlib.util
import json

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "rotation_coverage_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("rotation_coverage_audit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_rotation_coverage_audit_defines_same_ten_themes():
    m = load_module()
    assert len(m.THEMES) == 10
    labels = [label for label, _ in m.THEMES]
    assert labels == [
        "Semicondutores",
        "Biotecnologia",
        "Minerais & metais",
        "Agricultura",
        "Energia",
        "Defesa & aeroespacial",
        "IA & software",
        "Bancos",
        "Imobiliário",
        "Consumo discricionário",
    ]


def test_rotation_coverage_prefers_market_return():
    m = load_module()
    assert m.weekly_return({"market_return_5d_pct": 3.0, "opportunity_return_5d_pct": -2.0}) == 3.0
    assert m.weekly_return({"opportunity_return_5d_pct": -2.0}) is None

def test_rotation_coverage_audit_fails_closed_without_daily_inputs(tmp_path):
    m = load_module()
    payload = {
        "generated_at": "2026-10-06T00:00:00Z",
        "stocks": [
            {
                "ticker": "CHIP1",
                "quote_type": "EQUITY",
                "industry": "Semiconductors",
                "opportunity_return_5d_pct": 3.0,
            }
        ],
    }
    index = tmp_path / "stocks-index.json"
    out = tmp_path / "rotation_coverage_audit.json"
    index.write_text(json.dumps(payload), encoding="utf-8")
    original_index, original_out = m.INDEX, m.OUT
    try:
        m.INDEX, m.OUT = index, out
        try:
            m.main()
        except SystemExit as exc:
            assert "daily inputs absent" in str(exc)
        else:
            raise AssertionError("expected fail-closed audit")
    finally:
        m.INDEX, m.OUT = original_index, original_out

