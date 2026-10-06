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


class FakeScoredTicker:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


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

        with mock.patch.object(score_contract, "_load_core", return_value=(FakeScoredTicker, fake_core)):
            out = score_contract.score_universe(raw)

        self.assertEqual([x.ticker for x in captured], ["EQ", "UNK", "ETF1", "CC"])
        self.assertEqual({x.ticker for x in out}, {"MF", "FND"})
        for scored in out:
            self.assertIsNone(scored.score)
            self.assertEqual(scored.data_coverage_pct, 0)
            self.assertEqual(scored.metric_confidence, "low")
            self.assertEqual(scored.zombie_risk_state, "not_applicable")
            self.assertEqual(scored.zombie_risk_years, 0)
            self.assertEqual(scored.zombie_risk_support, [])
            self.assertEqual(scored.annual_zombie_history, [])
        self.assertEqual({x.quote_type for x in out}, {"MUTUALFUND", "FUND"})

    def test_failed_explicit_fund_is_preserved_but_never_scored(self):
        with mock.patch.object(score_contract, "_load_core", return_value=(FakeScoredTicker, lambda items: [])):
            out = score_contract.score_universe([row("BAD", "FUND", error="fetch failed")])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].ticker, "BAD")
        self.assertEqual(out[0].quote_type, "FUND")
        self.assertIsNone(out[0].score)
        self.assertEqual(out[0].data_coverage_pct, 0)

    def test_scoring_boundary_names_metric_confidence_explicitly(self):
        raw = [row("MF", "MUTUALFUND")]
        with mock.patch.object(score_contract, "_load_core", return_value=(FakeScoredTicker, lambda items: [])):
            out = score_contract.score_universe(raw)
        self.assertEqual(out[0].metric_confidence, "low")
        self.assertFalse(hasattr(out[0], "data_confidence"))


    def test_every_core_scoredticker_constructor_sets_zombie_contract(self):
        score_source = (SCRIPTS / "score.py").read_text(encoding="utf-8")
        starts = []
        pos = 0
        while True:
            pos = score_source.find("ScoredTicker(", pos)
            if pos < 0:
                break
            starts.append(pos)
            pos += len("ScoredTicker(")
        self.assertGreaterEqual(len(starts), 3)
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else score_source.find("\n\n    return out", start)
            block = score_source[start:end]
            for field in (
                "zombie_risk_state=",
                "zombie_risk_years=",
                "zombie_risk_reason=",
                "zombie_risk_support=",
                "annual_zombie_history=",
            ):
                self.assertIn(field, block, f"{field} missing from ScoredTicker constructor #{i + 1}")

    def test_run_routes_through_boundary_and_core_score_source_is_untouched(self):
        run_source = (SCRIPTS / "run.py").read_text(encoding="utf-8")
        score_source = (SCRIPTS / "score.py").read_text(encoding="utf-8")
        self.assertIn("from score_contract import score_universe", run_source)
        self.assertNotIn("from score import score_universe", run_source)
        self.assertIn('equities = [r for r in raw if r.quote_type not in ("ETF", "CRYPTO") and r.error is None]', score_source)
        self.assertNotIn("from asset_types import", score_source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
