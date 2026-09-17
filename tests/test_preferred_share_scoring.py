from pathlib import Path
from types import SimpleNamespace
import json
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import score_contract


class FakeScoredTicker:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def row(ticker, quote_type="EQUITY"):
    return SimpleNamespace(
        ticker=ticker,
        name=ticker,
        business_summary=None,
        sector="Utilities",
        industry=None,
        market_cap=None,
        currency="USD",
        quote_type=quote_type,
        error=None,
        expense_ratio=None,
        current_price=22.73,
    )


class PreferredShareScoringTests(unittest.TestCase):
    def empty_snapshot(self):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump({"stocks": []}, tmp)
        tmp.close()
        self.addCleanup(lambda: Path(tmp.name).unlink(missing_ok=True))
        return Path(tmp.name)

    def test_provider_equity_label_cannot_score_preferred_issue_as_common_stock(self):
        preferred = row("DUK-PA", "EQUITY")
        captured = []

        def fake_core(items):
            captured.extend(items)
            return []

        with mock.patch.object(score_contract, "_load_core", return_value=(FakeScoredTicker, fake_core)):
            out = score_contract.score_universe([preferred], previous_path=self.empty_snapshot())

        self.assertEqual(captured, [])
        self.assertEqual(preferred.quote_type, "PREFERRED")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].quote_type, "PREFERRED")
        self.assertIsNone(out[0].score)
        self.assertIsNone(out[0].value_pct)
        self.assertIsNone(out[0].growth_pct)
        self.assertEqual(out[0].data_coverage_pct, 0)

    def test_normal_share_class_ticker_still_reaches_common_equity_engine(self):
        common = row("BRK-B", "EQUITY")
        captured = []

        def fake_core(items):
            captured.extend(items)
            return []

        with mock.patch.object(score_contract, "_load_core", return_value=(FakeScoredTicker, fake_core)):
            out = score_contract.score_universe([common], previous_path=self.empty_snapshot())

        self.assertEqual(captured, [common])
        self.assertEqual(common.quote_type, "EQUITY")
        self.assertEqual(out, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
