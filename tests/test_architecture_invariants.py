import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MarketShardIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = json.loads(read("data/stocks-index.json"))
        cls.manifest = json.loads(read("data/dossiers-manifest.json"))

    def test_index_and_manifest_cover_same_unique_tickers(self):
        index_tickers = {str(row.get("ticker") or "").upper() for row in self.index.get("stocks", []) if row.get("ticker")}
        manifest_tickers = {str(ticker).upper() for ticker in (self.manifest.get("tickers") or {})}
        self.assertEqual(index_tickers, manifest_tickers)

    def test_every_index_row_points_to_the_manifest_shard(self):
        tickers = self.manifest.get("tickers") or {}
        for row in self.index.get("stocks", []):
            ticker = str(row.get("ticker") or "").upper()
            if ticker:
                self.assertIn(ticker, tickers)

    def test_every_manifest_ticker_exists_in_its_shard(self):
        shards = self.manifest.get("shards") or {}
        tickers = self.manifest.get("tickers") or {}
        cache = {}
        for ticker, shard_id in tickers.items():
            if shard_id not in cache:
                path = ROOT / str(shards[shard_id])
                cache[shard_id] = json.loads(path.read_text(encoding="utf-8"))
            rows = cache[shard_id].get("stocks") or []
            self.assertTrue(any(str(row.get("ticker") or "").upper() == str(ticker).upper() for row in rows))


class PoliticiansAndCongressTests(unittest.TestCase):
    def test_browser_and_dossiers_use_canonical_snapshot_not_bargo(self):
        politicians = read("politicians.js")
        market = read("market.js")
        self.assertIn("data/politicians.json", politicians)
        self.assertIn("congress_trades", market)
        self.assertNotIn("www.bargo.ai", politicians)
        self.assertNotIn("www.bargo.ai", market)

    def test_pipeline_normalizes_official_stock_act_provenance(self):
        congress = read("scripts/congress.py")
        self.assertIn("official_house", congress)
        self.assertIn("official_senate", congress)

    def test_senate_enrichment_is_official_and_non_destructive(self):
        senate = read("scripts/enrich_politicians_senate.py")
        workflow = read(".github/workflows/update-politicians.yml")
        self.assertIn("efiling.senate.gov", senate)
        self.assertIn('"report_types": "[11]"', senate)
        self.assertIn("preserving House-only snapshot", senate)
        self.assertIn("python scripts/enrich_politicians_senate.py", workflow)

    def test_snapshot_has_normalized_stock_trades(self):
        payload = json.loads(read("data/politicians.json"))
        rows = payload.get("trades") or payload.get("rows") or []
        stock_rows = [r for r in rows if r.get("ticker")]
        self.assertTrue(stock_rows)

    def test_snapshot_is_current_and_explicit_about_coverage(self):
        payload = json.loads(read("data/politicians.json"))
        self.assertTrue(payload.get("generated_at"))
        self.assertTrue(payload.get("coverage") or payload.get("source") or payload.get("sources"))


class FrontendArchitectureTests(unittest.TestCase):
    def test_market_is_static_first_with_safe_live_overlay(self):
        market = read("market.js")
        self.assertIn("async function enrichTickerLive", market)
        self.assertIn("refreshOpenDossierLiveFields(s)", market)
        for field in ("current_price", "forward_pe", "roe", "revenue_growth", "fcf_yield"):
            self.assertIn(f'data-live-field="{field}"', market)
        self.assertNotIn("www.bargo.ai", market)

    def test_lazy_loader_prefers_native_index_and_shards(self):
        market = read("market.js")
        universe = read("market-static-universe.js")
        loader = read("market-data-loader.js")
        self.assertIn("VestraMarketStaticUniverse", market)
        self.assertIn("staticUniverse?.ensureLoaded", market)
        self.assertIn("stocks-startup.json", universe)
        self.assertIn("stocks-index.json", universe)
        candidates_match = re.search(r"const candidates\s*=\s*\[(.*?)\];", universe, re.S)
        self.assertIsNotNone(candidates_match)
        candidates = candidates_match.group(1)
        self.assertLess(candidates.index("stocks-startup.json"), candidates.index("stocks-index.json"))
        self.assertNotIn("stocks.json", candidates, "browser bootstrap must never include the full market snapshot")
        self.assertIn("cache: 'no-store'", universe)
        self.assertNotIn("window.fetch =", loader)
        self.assertIn("dossiers-manifest.json", loader)
        self.assertRegex(loader, r"data/dossiers")
        self.assertNotIn("stocks.json?full=1", loader, "dossier opening must never fall back to the full market payload")
        self.assertIn("const result=rawOpen(ticker);", loader, "dossier must open before background hydration")
        self.assertIn("hydrateOpenDossier(ticker);", loader)

    def test_storage_keys_and_cached_idb_connection_are_stable(self):
        storage = read("app-storage.js")
        for exact in (
            "const STORAGE_KEY = 'PF_STATE_V6';",
            "const DB_NAME = 'pf_v6';",
            "const DB_STORE = 'kv';",
        ):
            self.assertIn(exact, storage)
        self.assertIn("let dbPromise", storage)

    def test_asset_identity_collision_guards_remain(self):
        identity = read("app-asset-identity.js")
        self.assertIn("canonical", identity.lower())
        self.assertIn("isin", identity.lower())

    def test_worker_has_exact_production_origin_policy(self):
        worker = read("worker.js")
        self.assertIn("pedrossnunes.github.io", worker)


class ScoreInvariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(read("data/stocks.json"))

    def test_scores_and_dimensions_stay_in_unit_interval_percent_scale(self):
        for row in self.payload.get("stocks", []):
            for key in ("score", "quality_score", "growth_score", "valuation_score", "momentum_score"):
                value = row.get(key)
                if value is not None:
                    self.assertGreaterEqual(float(value), 0.0)
                    self.assertLessEqual(float(value), 100.0)

    def test_missing_core_metrics_are_not_serialized_as_nan_strings(self):
        for row in self.payload.get("stocks", []):
            for key in ("roe", "roa", "revenue_growth", "earnings_growth", "free_cash_flow"):
                self.assertNotEqual(str(row.get(key)).lower(), "nan")

    def test_catalog_and_carried_rows_are_not_actionable_opportunities(self):
        for row in self.payload.get("stocks", []):
            status = str(row.get("pipeline_status") or "")
            if status in {"catalog_only", "carried_forward"}:
                self.assertFalse(bool(row.get("opportunity_eligible")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
