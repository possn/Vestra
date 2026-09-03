from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import json
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import known_asset_identity
import score_contract


class FakeScoredTicker:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def row(ticker, quote_type=None, error=None):
    return SimpleNamespace(
        ticker=ticker,
        name=ticker,
        business_summary=None,
        sector=None,
        industry=None,
        market_cap=None,
        currency="EUR",
        quote_type=quote_type,
        error=error,
        expense_ratio=None,
        current_price=None,
    )


class KnownAssetIdentityTests(unittest.TestCase):
    def empty_snapshot(self):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump({"stocks": []}, tmp)
        tmp.close()
        self.addCleanup(lambda: Path(tmp.name).unlink(missing_ok=True))
        return Path(tmp.name)

    def test_confirmed_broker_symbols_are_exact_overrides(self):
        expected = {
            "AGIG": ("EQUITY", None),
            "BT.A.L": ("EQUITY", "GB0030913577"),
            "DN3.DE": ("EQUITY", "JP3481200008"),
            "QDVE.DE": ("ETF", "IE00B3WJKG14"),
            "QDVH.DE": ("ETF", "IE00B4JNQZ49"),
            "QSR": ("EQUITY", None),
            "SPY4.DE": ("ETF", "IE00B4YBJ215"),
            "SPYD.DE": ("ETF", "IE00B6YX5D40"),
            "SPYL.DE": ("ETF", "IE000XZSV718"),
            "U9UA.DE": ("EQUITY", "CA90348V3011"),
            "URNU.DE": ("ETF", "IE000NDWFGA5"),
            "V60A.DE": ("ETF", "IE00BMVB5P51"),
            "VGWD.DE": ("ETF", "IE00B8GKDB10"),
        }
        self.assertEqual(set(known_asset_identity.KNOWN_ASSET_IDENTITY), set(expected))
        for ticker, (quote_type, isin) in expected.items():
            override = known_asset_identity.exact_identity_override(ticker.lower())
            self.assertEqual(override["quote_type"], quote_type)
            self.assertEqual(override.get("isin"), isin)
        self.assertIsNone(known_asset_identity.exact_identity_override("SPY.DE"))

    def test_blank_known_etf_is_retyped_before_frozen_core(self):
        current = row("SPYL.DE", None)
        captured = []

        def fake_core(items):
            captured.extend(items)
            return []

        with mock.patch.object(score_contract, "_load_core", return_value=(FakeScoredTicker, fake_core)):
            out = score_contract.score_universe([current], previous_path=self.empty_snapshot())

        self.assertEqual(captured, [current])
        self.assertEqual(current.quote_type, "ETF")
        self.assertEqual(current.isin, "IE000XZSV718")
        self.assertIn("State Street", current.name)
        self.assertEqual(out, [])

    def test_blank_known_equity_is_retyped_before_frozen_core(self):
        current = row("U9UA.DE", None)
        captured = []

        def fake_core(items):
            captured.extend(items)
            return []

        with mock.patch.object(score_contract, "_load_core", return_value=(FakeScoredTicker, fake_core)):
            out = score_contract.score_universe([current], previous_path=self.empty_snapshot())

        self.assertEqual(captured, [current])
        self.assertEqual(current.quote_type, "EQUITY")
        self.assertEqual(current.isin, "CA90348V3011")
        self.assertIn("Ucore", current.name)
        self.assertEqual(out, [])

    def test_known_etf_with_fetch_error_survives_as_neutral_etf(self):
        current = row("VGWD.DE", None, error="Yahoo unavailable")
        with mock.patch.object(score_contract, "_load_core", return_value=(FakeScoredTicker, lambda items: [])):
            out = score_contract.score_universe([current], previous_path=self.empty_snapshot())
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].quote_type, "ETF")
        self.assertIsNone(out[0].score)
        self.assertEqual(out[0].data_coverage_pct, 0)

    def test_explicit_current_equity_conflict_is_never_overwritten(self):
        current = row("SPYD.DE", "EQUITY")
        captured = []

        def fake_core(items):
            captured.extend(items)
            return []

        with mock.patch.object(score_contract, "_load_core", return_value=(FakeScoredTicker, fake_core)):
            out = score_contract.score_universe([current], previous_path=self.empty_snapshot())
        self.assertEqual(captured, [current])
        self.assertEqual(current.quote_type, "EQUITY")
        self.assertFalse(hasattr(current, "isin"))
        self.assertEqual(out, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
