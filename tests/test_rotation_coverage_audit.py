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
