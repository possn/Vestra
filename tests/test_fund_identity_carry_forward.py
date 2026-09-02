import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import score_contract


def row(ticker, quote_type=None, error=None, price=None):
    return SimpleNamespace(
        ticker=ticker,
        name=ticker,
        business_summary=None,
        sector=None,
        industry=None,
        market_cap=None,
        currency="USD",
        quote_type=quote_type,
        error=error,
        expense_ratio=None,
        current_price=price,
    )


class FakeScoredTicker:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FundIdentityCarryForwardTests(unittest.TestCase):
    def snapshot(self, rows):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump({"stocks": rows}, tmp)
        tmp.close()
        self.addCleanup(lambda: Path(tmp.name).unlink(missing_ok=True))
        return Path(tmp.name)

    def run_boundary(self, raw, previous_rows):
        captured = []

        def fake_core(items):
            captured.extend(items)
            return []

        previous_path = self.snapshot(previous_rows)
        with mock.patch.object(score_contract, "_load_core", return_value=(FakeScoredTicker, fake_core)):
            out = score_contract.score_universe(raw, previous_path=previous_path)
        return captured, out

    def test_blank_type_carries_exact_prior_fund_identity_and_neutralizes_score(self):
        captured, out = self.run_boundary(
            [row("BUG", None, error="Yahoo throttled")],
            [{
                "ticker": "BUG",
                "quote_type": "ETF",
                "name": "Wrong lane ETF should not qualify as prior FUND",
                "score": 91,
            }, {
                "ticker": "MUTF",
                "quote_type": "MUTUALFUND",
                "name": "Prior Mutual Fund",
                "expense_ratio": 0.004,
                "current_price": 12.5,
                "score": 88,
            }],
        )
        self.assertEqual([x.ticker for x in captured], ["BUG"])
        self.assertEqual(out, [])

        captured, out = self.run_boundary(
            [row("MUTF", None, error="Yahoo throttled")],
            [{
                "ticker": "MUTF",
                "quote_type": "MUTUALFUND",
                "name": "Prior Mutual Fund",
                "expense_ratio": 0.004,
                "current_price": 12.5,
                "score": 88,
            }],
        )
        self.assertEqual(captured, [])
        self.assertEqual(len(out), 1)
        carried = out[0]
        self.assertEqual(carried.ticker, "MUTF")
        self.assertEqual(carried.quote_type, "MUTUALFUND")
        self.assertEqual(carried.name, "MUTF")  # current non-null identity label wins
        self.assertEqual(carried.expense_ratio, 0.004)
        self.assertEqual(carried.current_price, 12.5)
        self.assertIsNone(carried.score)
        self.assertEqual(carried.data_coverage_pct, 0)

    def test_explicit_current_equity_never_overwritten_by_prior_fund(self):
        current = row("ABC", "EQUITY")
        captured, out = self.run_boundary(
            [current],
            [{"ticker": "ABC", "quote_type": "FUND", "name": "Old Fund"}],
        )
        self.assertEqual(captured, [current])
        self.assertEqual(out, [])

    def test_blank_without_prior_fund_remains_legacy_candidate(self):
        current = row("UNK", None)
        captured, out = self.run_boundary([current], [])
        self.assertEqual(captured, [current])
        self.assertEqual(out, [])

    def test_explicit_current_fund_survives_fetch_error(self):
        current = row("FND", "FUND", error="partial fetch")
        captured, out = self.run_boundary([current], [])
        self.assertEqual(captured, [])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].quote_type, "FUND")
        self.assertIsNone(out[0].score)

    def test_previous_snapshot_requires_explicit_fund_type(self):
        previous_path = self.snapshot([
            {"ticker": "EQ", "quote_type": "EQUITY"},
            {"ticker": "ETF", "quote_type": "ETF"},
            {"ticker": "MF", "quote_type": "mutualfund"},
            {"ticker": "F", "quote_type": " fund "},
            {"ticker": "", "quote_type": "FUND"},
        ])
        found = score_contract._previous_funds(previous_path)
        self.assertEqual(set(found), {"MF", "F"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
