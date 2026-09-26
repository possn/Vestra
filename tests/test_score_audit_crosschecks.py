import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


benchmark = load_module("vestra_score_benchmark_audit", "score_benchmark_audit.py")
peer_shadow = load_module("vestra_score_peer_shadow", "score_peer_shadow.py")


class ScoreAuditCrosscheckTests(unittest.TestCase):
    def test_benchmark_and_peer_shadow_run_read_only_on_real_snapshot(self):
        original_benchmark_out = benchmark.OUT
        original_peer_out = peer_shadow.OUT
        stocks_before = benchmark.STOCKS.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            try:
                benchmark.OUT = tmp / "score_benchmark_audit.json"
                peer_shadow.OUT = tmp / "score_peer_shadow.json"
                benchmark.main()
                peer_shadow.main()
                bench = json.loads(benchmark.OUT.read_text(encoding="utf-8"))
                shadow = json.loads(peer_shadow.OUT.read_text(encoding="utf-8"))
            finally:
                benchmark.OUT = original_benchmark_out
                peer_shadow.OUT = original_peer_out

        self.assertEqual(benchmark.STOCKS.read_bytes(), stocks_before)
        self.assertTrue(bench["production_unchanged"])
        self.assertTrue(shadow["production_unchanged"])
        self.assertGreater(shadow["shadow_rows"], 0)

        benchmark_summary = {
            model: {
                "peer_rows": data["peer_rows"],
                "eligible_ratio": data["eligible_ratio"],
                "largest_median_percentile_shifts": sorted(
                    (
                        {
                            "field": item["field"],
                            "peer_observations": item["peer_observations"],
                            "median_absolute_percentile_shift": item["median_absolute_percentile_shift"],
                        }
                        for item in data["metrics"]
                        if item["median_absolute_percentile_shift"] is not None
                    ),
                    key=lambda item: item["median_absolute_percentile_shift"],
                    reverse=True,
                )[:4],
                "unavailable_metrics": [
                    item["field"] for item in data["metrics"]
                    if item["peer_observations"] == 0
                ],
            }
            for model, data in bench["models"].items()
        }
        peer_summary = {}
        for model, data in shadow["model_summaries"].items():
            peer_summary[model] = {
                "peer_rows": data["peer_rows"],
                "shadow_rows": data["shadow_rows"],
                "mean_delta_vs_raw": data["mean_delta_vs_raw"],
                "mean_absolute_delta_vs_raw": data["mean_absolute_delta_vs_raw"],
                "max_absolute_delta_vs_raw": data["max_absolute_delta_vs_raw"],
                "benchmark_scope_counts": data["benchmark_scope_counts"],
                "largest_rank_shifts": [
                    {
                        "ticker": item.get("ticker"),
                        "rank_shift": item.get("rank_shift"),
                        "delta_vs_raw": item.get("delta_vs_raw"),
                    }
                    for item in data["largest_rank_shifts"][:5]
                ],
            }

        print("SCORE_BENCHMARK_SUMMARY=" + json.dumps(benchmark_summary, sort_keys=True))
        print("SCORE_PEER_SHADOW_SUMMARY=" + json.dumps(peer_summary, sort_keys=True))

    def test_forward_validation_report_is_explicitly_prospective(self):
        report_path = ROOT / "data" / "score_validation_report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertIn("prospective", report["methodology"])
        self.assertIn("Do not optimize production weights", report["decision_rule"])
        compact = {
            "snapshots_available": report["snapshots_available"],
            "realised_outcomes": report["realised_outcomes"],
            "horizons": {
                horizon: {
                    "n": data["n"],
                    "cohort_count": data["cohort_count"],
                    "status": data["status"],
                    "rank_information_coefficient": data["rank_information_coefficient"],
                    "median_cohort_rank_ic": data["median_cohort_rank_ic"],
                    "top_minus_bottom_pct": data.get("top_minus_bottom_pct"),
                    "median_cohort_top_minus_bottom_pct": data.get("median_cohort_top_minus_bottom_pct"),
                    "peer_shadow_eligible_n": data["peer_shadow_comparison"]["eligible_n"],
                }
                for horizon, data in report["horizons"].items()
            },
        }
        print("SCORE_FORWARD_SUMMARY=" + json.dumps(compact, sort_keys=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
