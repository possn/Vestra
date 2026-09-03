import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import valuation


class ValuationMissingConfidenceTests(unittest.TestCase):
    def _row(self, confidence_marker=False):
        row = {
            "current_price": 100.0,
            "score_model": "general",
            "quote_type": "EQUITY",
            "forward_pe": 10.0,
            "sector_forward_pe_median": 20.0,
            "risk_gate": "clear",
        }
        if confidence_marker:
            row["confidence_score"] = 80.0
        return row

    def test_missing_confidence_is_explicitly_conservative(self):
        result = valuation.assess(self._row(False))
        self.assertEqual(result["valuation_signal"], "uncertain")
        self.assertEqual(result["valuation_confidence"], "low")
        self.assertIn("confiança global ausente", result["valuation_note"])

    def test_observed_confidence_can_unlock_valuation_signal(self):
        result = valuation.assess(self._row(True))
        self.assertEqual(result["valuation_signal"], "undervalued")
        self.assertEqual(result["valuation_confidence"], "low")
        self.assertNotIn("confiança global ausente", result["valuation_note"])

    def test_source_does_not_coerce_missing_confidence_to_zero(self):
        source = (SCRIPTS / "valuation.py").read_text(encoding="utf-8")
        self.assertNotIn("_n(row.get('confidence_score')) or 0.0", source)
        self.assertIn("confidence_missing=conf_score is None", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
