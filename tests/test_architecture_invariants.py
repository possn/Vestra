from __future__ import annotations

import datetime as dt
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def load(path: str):
    return json.loads(read(path))


class MarketShardIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = load("data/stocks-index.json")
        cls.manifest = load("data/dossiers-manifest.json")
        cls.rows = cls.index.get("stocks") or []
        cls.manifest_map = cls.manifest.get("tickers") or {}

    def test_index_and_manifest_cover_same_unique_tickers(self):
        index_tickers = [str(r.get("ticker") or "") for r in self.rows]
        self.assertEqual(len(index_tickers), len(set(index_tickers)), "duplicate tickers in market index")
        self.assertEqual(set(index_tickers), set(self.manifest_map), "index/manifest ticker mismatch")
        self.assertEqual(self.manifest.get("ticker_count"), len(index_tickers))

    def test_every_index_row_points_to_the_manifest_shard(self):
        for row in self.rows:
            ticker = row["ticker"]
            self.assertEqual(row.get("dossier_shard"), self.manifest_map[ticker], ticker)

    def test_every_manifest_ticker_exists_in_its_shard(self):
        by_shard: dict[str, list[str]] = {}
        for ticker, shard in self.manifest_map.items():
            by_shard.setdefault(str(shard), []).append(ticker)
        for shard, tickers in by_shard.items():
            path = DATA / "dossiers" / f"{shard}.json"
            self.assertTrue(path.exists(), f"missing dossier shard {shard}")
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(str(payload.get("shard")), shard)
            stocks = payload.get("stocks") or {}
            missing = sorted(set(tickers) - set(stocks))
            self.assertFalse(missing, f"{shard}: missing {missing[:10]}")
            for ticker in tickers:
                self.assertEqual(stocks[ticker].get("ticker"), ticker)


class PoliticiansAndCongressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.feed = load("data/politicians.json")

    def test_snapshot_is_current_and_explicit_about_coverage(self):
        self.assertGreaterEqual(int(self.feed.get("schema_version") or 0), 2)
        newest = dt.date.fromisoformat(self.feed["newest_disclosure"][:10])
        age = (dt.date.today() - newest).days
        self.assertLessEqual(age, 60, f"politicians snapshot stale by {age} days")
        coverage = set(self.feed.get("coverage_chambers") or [])
        self.assertTrue(coverage)
        self.assertTrue(coverage <= {"House", "Senate"})

    def test_snapshot_has_normalized_stock_trades(self):
        trades = self.feed.get("trades") or []
        self.assertGreaterEqual(len(trades), 10)
        for trade in trades:
            self.assertTrue(trade.get("ticker"))
            self.assertTrue(trade.get("member"))
            self.assertTrue(trade.get("transaction_date"))
            self.assertTrue(trade.get("disclosure_date"))
            self.assertIn(str(trade.get("type") or "").lower(), {"buy", "sell", "trade", "exchange"})

    def test_browser_and_dossiers_use_canonical_snapshot_not_bargo(self):
        market = read("market.js")
        politicians = read("politicians.js")
        congress = read("scripts/congress.py")
        worker = read("worker.js")
        combined = "\n".join((market, politicians, congress, worker)).lower()
        self.assertIn("data/politicians.json", market)
        self.assertIn("data/politicians.json", politicians)
        self.assertNotIn("bargo.ai", combined)
        self.assertNotIn('url.pathname === "/congress"', worker)

    def test_pipeline_provenance_names_official_stock_act_source(self):
        run = read("scripts/run.py")
        self.assertNotIn('row["data_sources"].append("STOCK Act / Bargo")', run)
        self.assertIn('row["data_sources"].append("U.S. House Clerk / STOCK Act")', run)


class FrontendArchitectureTests(unittest.TestCase):
    def test_market_is_static_first_with_safe_live_overlay(self):
        market = read("market.js")
        self.assertIn("async function enrichTickerLive", market)
        self.assertIn("refreshOpenDossierLiveFields(s)", market)
        for field in ("current_price", "forward_pe", "roe", "revenue_growth", "fcf_yield"):
            self.assertIn(f'data-live-field="{field}"', market)
        self.assertNotIn("www.bargo.ai", market)

    def test_lazy_loader_prefers_index_and_shards(self):
        loader = read("market-data-loader.js")
        self.assertIn("stocks-index.json", loader)
        self.assertIn("dossiers-manifest.json", loader)
        self.assertRegex(loader, r"data/dossiers")
        # Full stocks is permitted only as an explicit emergency fallback.
        for match in re.finditer(r"stocks\.json", loader):
            window = loader[max(0, match.start() - 120): match.end() + 120]
            self.assertTrue("full=1" in window or "legacy" in window.lower() or "intercept" in window.lower(), window)

    def test_storage_keys_and_cached_idb_connection_are_stable(self):
        storage = read("app-storage.js")
        for exact in (
            "const STORAGE_KEY = 'PF_STATE_V6';",
            "const DB_NAME = 'pf_v6';",
            "const DB_STORE = 'kv';",
            "const DB_KEY = 'state';",
            "let _idbConn = null;",
            "if (_idbConn) return _idbConn;",
        ):
            self.assertIn(exact, storage)

    def test_asset_identity_collision_guards_remain(self):
        identity = read("app-asset-identity.js")
        self.assertIn('"PTCOR0AE0006":"COR.LS"', identity)
        self.assertIn('"BTC":"BTC-USD"', identity)
        self.assertIn('"ETH":"ETH-USD"', identity)

    def test_worker_has_exact_production_origin_policy(self):
        worker = read("worker.js")
        self.assertIn('u.origin === "https://possn.github.io"', worker)
        self.assertNotIn('includes("github.io")', worker)
        self.assertNotIn('includes("pages.dev")', worker)


if __name__ == "__main__":
    unittest.main(verbosity=2)
