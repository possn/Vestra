import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import sync_learned_universe as sync


ROOT = Path(__file__).resolve().parents[1]


class LearnedUniversePipelineTests(unittest.TestCase):
    def test_valid_rows_reject_invalid_symbols_and_asset_types(self):
        payload = {
            "rows": [
                {"ticker": "new1", "quote_type": "EQUITY", "name": "New One"},
                {"ticker": "BAD SYMBOL", "quote_type": "EQUITY"},
                {"ticker": "BTC-USD", "quote_type": "CRYPTOCURRENCY"},
                {"ticker": "fund.l", "quote_type": "ETF"},
            ]
        }
        rows = sync._valid_rows(payload)
        self.assertEqual([r["ticker"] for r in rows], ["FUND.L", "NEW1"])
        self.assertEqual(rows[1]["name"], "New One")

    def test_remote_discovery_is_snapshotted_and_added_to_extra_universe(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            snapshot = root / "learned_tickers.json"
            extra = root / "extra_tickers.json"
            snapshot.write_text(json.dumps({"schema_version": 1, "rows": []}), encoding="utf-8")
            extra.write_text(json.dumps({"tickers": ["EXIST"]}), encoding="utf-8")
            remote = [{
                "ticker": "ZZVST",
                "name": "Vestra Synthetic",
                "exchange": "NMS",
                "currency": "USD",
                "quote_type": "EQUITY",
                "sector": "Technology",
                "industry": "Software",
                "country": "US",
                "first_seen": "2026-08-31T10:00:00Z",
                "last_seen": "2026-08-31T11:00:00Z",
                "validation_count": 2,
            }]
            with mock.patch.object(sync, "SNAPSHOT_PATH", snapshot), \
                 mock.patch.object(sync, "EXTRA_PATH", extra), \
                 mock.patch.object(sync, "fetch_remote_rows", return_value=remote):
                sync.main()

            snap = json.loads(snapshot.read_text(encoding="utf-8"))
            merged = json.loads(extra.read_text(encoding="utf-8"))
            self.assertEqual(snap["source"], "snapshot+worker")
            self.assertEqual(snap["count"], 1)
            self.assertEqual(snap["rows"][0]["ticker"], "ZZVST")
            self.assertEqual(merged["tickers"], ["EXIST", "ZZVST"])
            self.assertEqual(merged["learned_from_search"], 1)
            self.assertEqual(merged["learned_snapshot"], "data/learned_tickers.json")

    def test_worker_outage_preserves_previous_snapshot_and_extra_membership(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            snapshot = root / "learned_tickers.json"
            extra = root / "extra_tickers.json"
            snapshot.write_text(json.dumps({
                "schema_version": 1,
                "rows": [{"ticker": "KEEP", "quote_type": "EQUITY", "validation_count": 3}],
            }), encoding="utf-8")
            extra.write_text(json.dumps({"tickers": []}), encoding="utf-8")
            with mock.patch.object(sync, "SNAPSHOT_PATH", snapshot), \
                 mock.patch.object(sync, "EXTRA_PATH", extra), \
                 mock.patch.object(sync, "fetch_remote_rows", side_effect=OSError("offline")):
                sync.main()

            snap = json.loads(snapshot.read_text(encoding="utf-8"))
            merged = json.loads(extra.read_text(encoding="utf-8"))
            self.assertEqual(snap["source"], "snapshot-fallback")
            self.assertEqual([r["ticker"] for r in snap["rows"]], ["KEEP"])
            self.assertEqual(merged["tickers"], ["KEEP"])

    def test_run_pipeline_fetches_learned_names_before_other_portfolio_names(self):
        source = (ROOT / "scripts" / "run.py").read_text(encoding="utf-8")
        learned = source.index("raw_learned = fetch_many(learned_tickers, workers_override=1, retries=3")
        portfolio = source.index("raw_portfolio = fetch_many(portfolio_remainder, workers_override=3, retries=2")
        remainder = source.index("raw_remainder = fetch_many(remainder_tickers, retries=1)")
        self.assertLess(learned, portfolio)
        self.assertLess(portfolio, remainder)
        self.assertIn("missing_learned = [t for t in learned_tickers if t not in scored_now]", source)
        self.assertIn('log.error("Learned ticker promotion incomplete:', source)

    def test_market_workflow_syncs_learned_universe_before_pipeline(self):
        source = (ROOT / ".github" / "workflows" / "update-market-data.yml").read_text(encoding="utf-8")
        sync_step = source.index("- name: Sync learned search universe")
        run_step = source.index("- name: Run pipeline")
        self.assertLess(sync_step, run_step)
        self.assertIn("run: python sync_learned_universe.py", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
