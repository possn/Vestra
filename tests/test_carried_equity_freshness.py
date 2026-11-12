"""A carried equity cannot reappear as a current Discovery opportunity."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import postprocess_market as postprocess


class CarriedEquityFreshnessTests(unittest.TestCase):
    def test_rotating_carried_equity_drops_stale_rank_and_scanner(self):
        stale = {
            "ticker": "OLD", "quote_type": "EQUITY",
            "pipeline_status": "equity_carried_forward_rotating",
            "opportunity_score": 95, "opportunity_eligible": True,
            "opportunity_label": "Prioridade elevada",
            "opportunity_timing_score": 91,
            "opportunity_featured": True,
            "recovery_status": "confirmed", "recovery_score": 84,
            "opportunity_reasons": ["evidência anterior"],
            "opportunity_timing_score": 90,
            "scanner_tags": ["best_opportunities"],
            "scanner_results": {"best_opportunities": {"score": 95}},
            "scanner_best": "best_opportunities",
            "low52_status": "opportunity", "low52_score": 88,
            "low52_opportunity_score": 88,
        }
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "stocks.json"
            path.write_text(json.dumps({
                "generated_at": "2026-11-12T06:00:00Z",
                "stocks": [stale],
            }), encoding="utf-8")
            with (patch.object(postprocess, "STOCKS_PATH", str(path)),
                  patch.object(postprocess, "load_fund_aum_history", return_value={}),
                  patch.object(postprocess, "update_fund_aum_history", return_value={}),
                  patch.object(postprocess, "_rotation_context", return_value={}),
                  patch.object(postprocess, "_market_regime_context", return_value={}),
                  patch.object(postprocess, "assess_opportunity", side_effect=AssertionError(
                      "carried-forward rows cannot be re-ranked"))):
                postprocess.main()
            result = json.loads(path.read_text(encoding="utf-8"))
        row = result["stocks"][0]
        self.assertIs(row["opportunity_eligible"], False)
        self.assertIsNone(row["opportunity_score"])
        self.assertEqual(row["opportunity_label"], "Dados insuficientes")
        self.assertNotIn("opportunity_timing_score", row)
        self.assertNotIn("opportunity_featured", row)
        self.assertEqual(row["recovery_status"], "insufficient")
        self.assertIsNone(row["recovery_score"])
        self.assertEqual(row["low52_status"], "insufficient")
        self.assertIsNone(row["low52_score"])
        self.assertNotIn("low52_opportunity_score", row)
        self.assertEqual(row["scanner_tags"], [])
        self.assertEqual(row["scanner_results"], {})
        self.assertNotIn("scanner_best", row)
        self.assertEqual(result["postprocess_market"]["stale_rows_sanitized"], 1)
        self.assertEqual(result["postprocess_market"]["opportunity_rows_refreshed"], 0)

    def test_other_documented_carried_states_are_still_sanitized(self):
        for status in ("equity_catalog_only", "equity_carried_forward"):
            with self.subTest(status=status):
                row = {"pipeline_status": status, "opportunity_score": 99,
                       "opportunity_eligible": True, "scanner_best": "best_opportunities"}
                postprocess._sanitize_carried(row)
                self.assertFalse(row["opportunity_eligible"])
                self.assertIsNone(row["opportunity_score"])
                self.assertNotIn("scanner_best", row)


if __name__ == "__main__":
    unittest.main()
