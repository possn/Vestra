import importlib.util
import os
from pathlib import Path
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# Architecture CI intentionally does not install the full market requirements.
# analyst.py only needs the yfinance symbol at import time; network behavior is
# replaced below with deterministic fetch_one stubs.
sys.modules.setdefault("yfinance", types.SimpleNamespace(Ticker=lambda ticker: None))
MODULE_PATH = SCRIPTS / "analyst.py"
spec = importlib.util.spec_from_file_location("analyst_rotation_test", MODULE_PATH)
analyst = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = analyst
spec.loader.exec_module(analyst)


class AnalystRotationTests(unittest.TestCase):
    def _row(self, ticker, score=50, market_cap=1_000_000):
        return {
            "ticker": ticker,
            "quote_type": "EQUITY",
            "score": score,
            "market_cap": market_cap,
            "current_price": 10,
        }

    def _fresh_previous(self, ticker, coverage=66.7):
        return {
            "ticker": ticker,
            "status": "ok",
            "coverage_pct": coverage,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "eps_next_q": 1.23,
        }

    def test_priority_is_always_refreshed_and_missing_nonpriority_wins_rotation(self):
        rows = [self._row("P"), self._row("A", score=10), self._row("C", score=99)]
        previous = {"C": self._fresh_previous("C")}
        called = []

        def fake_fetch(ticker, current_price=None):
            called.append(ticker)
            return analyst.AnalystSnapshot(
                ticker=ticker,
                status="ok",
                coverage_pct=66.7,
                fetched_at=datetime.now(timezone.utc).isoformat(),
                eps_next_q=2.0,
            )

        env = {
            "FINSCANNER_ANALYST_MAX": "10",
            "FINSCANNER_ANALYST_NONPRIORITY_REFRESH": "1",
            "FINSCANNER_ANALYST_CACHE_MAX_AGE_DAYS": "14",
            "FINSCANNER_ANALYST_WORKERS": "1",
        }
        with patch.dict(os.environ, env, clear=False), \
             patch.object(analyst, "_load_previous_snapshots", return_value=previous), \
             patch.object(analyst, "fetch_one", side_effect=fake_fetch):
            out = analyst.fetch_many(rows, priority_tickers={"P"})

        self.assertEqual(called, ["P", "A"])
        self.assertEqual(out["P"]["refresh_state"], "fresh")
        self.assertEqual(out["A"]["refresh_state"], "fresh")
        self.assertEqual(out["C"]["refresh_state"], "cached_rotation")
        self.assertEqual(out["C"]["eps_next_q"], 1.23)

    def test_zero_coverage_refresh_does_not_erase_recent_validated_snapshot(self):
        previous = {"P": self._fresh_previous("P")}

        def failed_fetch(ticker, current_price=None):
            return analyst.AnalystSnapshot(
                ticker=ticker,
                status="not_available",
                coverage_pct=0.0,
                fetched_at=datetime.now(timezone.utc).isoformat(),
            )

        env = {
            "FINSCANNER_ANALYST_MAX": "10",
            "FINSCANNER_ANALYST_NONPRIORITY_REFRESH": "0",
            "FINSCANNER_ANALYST_CACHE_MAX_AGE_DAYS": "14",
            "FINSCANNER_ANALYST_WORKERS": "1",
        }
        with patch.dict(os.environ, env, clear=False), \
             patch.object(analyst, "_load_previous_snapshots", return_value=previous), \
             patch.object(analyst, "fetch_one", side_effect=failed_fetch):
            out = analyst.fetch_many([self._row("P")], priority_tickers={"P"})

        self.assertEqual(out["P"]["refresh_state"], "cached_after_refresh_failure")
        self.assertEqual(out["P"]["coverage_pct"], 66.7)
        self.assertEqual(out["P"]["eps_next_q"], 1.23)

    def test_expired_snapshot_is_not_carried_when_not_selected(self):
        old = self._fresh_previous("C")
        old["fetched_at"] = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        env = {
            "FINSCANNER_ANALYST_MAX": "10",
            "FINSCANNER_ANALYST_NONPRIORITY_REFRESH": "0",
            "FINSCANNER_ANALYST_CACHE_MAX_AGE_DAYS": "14",
            "FINSCANNER_ANALYST_WORKERS": "1",
        }
        with patch.dict(os.environ, env, clear=False), \
             patch.object(analyst, "_load_previous_snapshots", return_value={"C": old}), \
             patch.object(analyst, "fetch_one") as fetch_one:
            out = analyst.fetch_many([self._row("C")], priority_tickers=set())

        fetch_one.assert_not_called()
        self.assertNotIn("C", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
