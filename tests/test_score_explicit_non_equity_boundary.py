from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import score_contract


def row(ticker, quote_type, error=None):
    return SimpleNamespace(
        ticker=ticker,
        name=ticker,
        business_summary=None,
        sector="Test",
        industry="Test",
        market_cap=100.0,
        currency="USD",
        quote_type=quote_type,
        error=error,
        expense_ratio=None,
        current_price=10.0,
    )


class ScoreExplicitNonEquityBoundaryTests(unittest.TestCase):
    def test_funds_are_removed_before_core_but_unresolved_stays_candidate(self):
        raw = [
            row("EQ", "EQUITY"),
            row("UNK", None),
            row("ETF1", "ETF"),
            row("CC", "CRYPTO"),
            row("MF", "MUTUALFUND"),
            row("FND", "fund"),
        ]
        captured = []

        def fake_core(items):
            captured.extend(items)
            return []

        with mock.patch.object(score_contract, "_core_score_universe", side_effect=fake_core):
            out = score_contract.score_universe(raw)

        self.assertEqual([x.ticker for x in captured], ["EQ", "UNK", "ETF1", "CC"])
        self.assertEqual({x.ticker for x in out}, {"MF", "FND"})
        for scored in out:
            self.assertIsNone(scored.score)
            self.assertEqual(scored.data_coverage_pct, 0)
            self.assertEqual(scored.data_confidence, "low")
        self.assertEqual({x.quote_type for x in out}, {"MUTUALFUND", "FUND"})

    def test_failed_fund_is_not_reintroduced(self):
        with mock.patch.object(score_contract, "_core_score_universe", return_value=[]):
            out = score_contract.score_universe([row("BAD", "FUND", error="fetch failed")])
        self.assertEqual(out, [])

    def test_run_routes_through_boundary_and_core_score_source_is_untouched(self):
        run_source = (SCRIPTS / "run.py").read_text(encoding="utf-8")
        score_source = (SCRIPTS / "score.py").read_text(encoding="utf-8")
        self.assertIn("from score_contract import score_universe", run_source)
        self.assertNotIn("from score import score_universe", run_source)
        self.assertIn('equities = [r for r in raw if r.quote_type not in ("ETF", "CRYPTO") and r.error is None]', score_source)
        self.assertNotIn("from asset_types import", score_source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
