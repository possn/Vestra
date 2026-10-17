import sys
import unittest
from pathlib import Path
from types import SimpleNamespace, ModuleType
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from score import _score_model_for, _benchmark_values, _percentile_rank, _avg
from audit_biotech_live_input_parity import measure


class LiveInputParityTests(unittest.TestCase):
    def test_uses_exact_input_and_one_decimal_published_values(self):
        raw = []
        for i in range(25):
            raw.append(SimpleNamespace(
                ticker=f"BT{i}", quote_type="EQUITY", error=None,
                sector="Healthcare", industry="Biotechnology",
                gross_margin=0.10 + i * 0.01, roa=-0.40 + i * 0.02,
            ))
        scored = []
        for row in raw:
            expected = _avg([
                _percentile_rank(row.gross_margin, [x.gross_margin for x in raw]),
                _percentile_rank(row.roa, [x.roa for x in raw]),
            ])
            scored.append(SimpleNamespace(ticker=row.ticker,
                score_dimensions={"Operating Quality": round(expected, 1)}))
        output = measure(raw, scored)
        self.assertEqual(output["biotech_input_rows"], 25)
        self.assertEqual(output["comparable_rows"], 25)
        self.assertEqual(output["outside_rounding_tolerance"], 0)
        self.assertEqual(output["max_absolute_parity_delta"], 0)

    def test_detects_a_real_mismatch_without_changing_scores(self):
        raw = [SimpleNamespace(ticker=f"BT{i}", quote_type="EQUITY", error=None,
                 sector="Healthcare", industry="Biotechnology",
                 gross_margin=i/25, roa=i/40) for i in range(25)]
        scored = [SimpleNamespace(ticker=row.ticker,
                 score_dimensions={"Operating Quality": 50.0}) for row in raw]
        before = [x.score_dimensions.copy() for x in scored]
        output = measure(raw, scored)
        self.assertGreater(output["outside_rounding_tolerance"], 0)
        self.assertEqual([x.score_dimensions for x in scored], before)


if __name__ == "__main__":
    unittest.main()
