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
