import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prebreakout_funnel_timeseries as m


def test_aggregates_counts_and_skips_bad_files(tmp_path):
    d = tmp_path / "2026"; d.mkdir()
    (d / "a.json").write_text(json.dumps({"attempted": 10, "generated_at": "x",
        "gate_funnel": {"first_rejection_counts": {"moving_average_structure": 8, "base_width": 2}}}))
    (d / "b.json").write_text(json.dumps({"attempted": 10,
        "gate_funnel": {"first_rejection_counts": {"moving_average_structure": 6}}}))
    (d / "bad.json").write_text("{not json")
    (d / "c.json").write_text(json.dumps({"attempted": 0, "gate_funnel": {"first_rejection_counts": {"x": 1}}}))
    out = m.build(str(tmp_path / "*" / "*.json"))
    assert out["slots"] == 2 and out["attempted_total"] == 20
    assert out["first_rejection_totals"]["moving_average_structure"] == 14
    assert out["first_rejection_share_of_attempted"]["moving_average_structure"] == 0.7


def test_default_uses_slots_without_daily_duplicates(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "ROOT", str(tmp_path))
    year = tmp_path / "data" / "prebreakout-history" / "2026"
    slots = year / "slots"
    slots.mkdir(parents=True)
    def save(path, attempted, counts):
        path.write_text(json.dumps({"attempted": attempted, "gate_funnel": {"first_rejection_counts": counts}}))
    save(year / "2026-11-26.json", 10, {"base_width": 10})
    save(slots / "2026-11-26-slot0.json", 10, {"base_width": 10})
    save(slots / "2026-11-26-slot1.json", 20, {"moving_average_structure": 20, "bad": True, "negative": -1})
    out = m.build()
    assert out["slots"] == 2 and out["attempted_total"] == 30
    assert out["first_rejection_totals"] == {"base_width": 10, "moving_average_structure": 20}
