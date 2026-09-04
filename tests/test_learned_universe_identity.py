import json
import tempfile
import unittest
from pathlib import Path

from scripts import sync_learned_universe as sync


ROOT = Path(__file__).resolve().parents[1]


class LearnedUniverseIdentityTests(unittest.TestCase):
    def test_worker_requires_exact_provider_symbol_and_v2_namespace(self):
        source = (ROOT / "worker-router.js").read_text(encoding="utf-8")
        self.assertIn("vestra-learned-universe-v2", source)
        self.assertIn("fetchYahooExactIdentity", source)
        self.assertIn("txt(item?.symbol).toUpperCase()===ticker", source)
        self.assertIn("exactIdentity.symbol !== ticker", source)
        self.assertIn("canonical !== ticker || retrieval !== ticker", source)

    def test_local_catalogue_uses_clean_v2_storage_key(self):
        source = (ROOT / "market-learned-universe.js").read_text(encoding="utf-8")
        self.assertIn("market_learned_universe_v2", source)
        self.assertIn("const SCHEMA_VERSION = 2", source)
        self.assertIn("version: '2.0'", source)

    def test_only_legacy_learned_and_unresolved_rows_are_retired(self):
        with tempfile.TemporaryDirectory() as tmp:
            extra_path = Path(tmp) / "extra_tickers.json"
            extra_path.write_text(
                json.dumps({"tickers": ["KEEP", "BAD", "GOOD"]}),
                encoding="utf-8",
            )
            old_extra = sync.EXTRA_PATH
            try:
                sync.EXTRA_PATH = extra_path
                current = [{"ticker": "GOOD"}, {"ticker": "NEW"}]
                previous = [{"ticker": "BAD"}, {"ticker": "GOOD"}]
                hygiene = {"unresolved_tickers": ["BAD", "OTHER"]}
                before, after, retired = sync.merge_extra_tickers(current, previous, hygiene)
            finally:
                sync.EXTRA_PATH = old_extra

            payload = json.loads(extra_path.read_text(encoding="utf-8"))
            self.assertEqual(before, 3)
            self.assertEqual(after, 3)
            self.assertEqual(retired, ["BAD"])
            self.assertEqual(payload["tickers"], ["GOOD", "KEEP", "NEW"])
            self.assertEqual(payload["retired_unverified_learned"], ["BAD"])
            self.assertEqual(payload["learned_identity_schema"], 2)

    def test_reachable_worker_is_authoritative_not_snapshot_union(self):
        source = (ROOT / "scripts" / "sync_learned_universe.py").read_text(encoding="utf-8")
        self.assertIn('source = "worker-authoritative-v2"', source)
        self.assertNotIn("_merge_rows(previous, remote)", source)


if __name__ == "__main__":
    unittest.main()
