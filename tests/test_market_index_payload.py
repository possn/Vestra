import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_market_shards as shards


class MarketIndexPayloadTests(unittest.TestCase):
    def test_detail_only_text_lists_stay_out_of_startup_index(self):
        source = {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "score": 82.0,
            "data_sources": ["Yahoo Finance", "SEC"],
            "opportunity_reasons": ["Strong quality"],
            "opportunity_cautions": ["Valuation"],
            "scanner_reasons": ["Scanner reason"],
            "scanner_cautions": ["Scanner caution"],
            "thesis_reasons": ["Thesis reason"],
            "thesis_cautions": ["Thesis caution"],
        }

        row = shards.index_row(source)

        for key in shards.DETAIL_ONLY_LIST_KEYS:
            self.assertNotIn(key, row)
        self.assertEqual(row["ticker"], "AAPL")
        self.assertEqual(row["score"], 82.0)
        self.assertEqual(row["dossier_shard"], "A0")

    def test_dossier_shards_are_deterministic_and_split_each_prefix(self):
        self.assertEqual(shards.SHARD_BUCKETS, 4)
        self.assertEqual(shards.shard_for("AAPL"), "A0")
        self.assertEqual(shards.shard_for("MSFT"), "M3")
        self.assertEqual(shards.shard_for("air.pa"), "A3")
        self.assertRegex(shards.shard_for("BRK-B"), r"^B[0-3]$")
        sample = {shards.shard_for(f"A{i}") for i in range(40)}
        self.assertGreaterEqual(len(sample), 3, "a busy prefix should distribute across multiple buckets")

    def test_scanner_results_move_to_lazy_payload(self):
        scanner_results = {
            "best_opportunities": {
                "score": 77.0,
                "label": "Strong",
                "reason": "Ranking structural evidence-gated",
            },
            "fallen_angels": {
                "score": 69.0,
                "label": "Fallen Angels",
                "reasons": ["Near 52w low", "Balance sheet adequate"],
            },
        }
        source = {"ticker": "MSFT", "scanner_results": scanner_results}
        row = shards.index_row(source)
        self.assertNotIn("scanner_results", row)
        self.assertEqual(shards.scanner_results(source), scanner_results)

    def test_empty_scanner_results_are_not_emitted(self):
        self.assertIsNone(shards.scanner_results({"ticker": "MSFT", "scanner_results": {}}))
        self.assertIsNone(shards.scanner_results({"ticker": "MSFT", "scanner_results": []}))

    def test_full_history_is_not_copied_but_compact_52_week_bounds_are_kept(self):
        row = shards.index_row({
            "ticker": "TEST",
            "price_history_1y": [
                {"close": 120.0},
                {"close": 95.0},
                {"close": 140.0},
                {"close": 110.0},
            ],
        })
        self.assertNotIn("price_history_1y", row)
        self.assertEqual(row["fifty_two_week_low"], 95.0)
        self.assertEqual(row["fifty_two_week_high"], 140.0)
        self.assertEqual(row["low52_price_low"], 95.0)
        self.assertEqual(row["low52_price_high"], 140.0)

    def test_funds_keep_compact_aum_and_top10_concentration_without_holdings_list(self):
        row = shards.index_row({
            "ticker": "FUND",
            "quote_type": "ETF",
            "fund_total_assets": 5_000_000_000,
            "top_holdings": [
                {"holdingPercent": 0.08},
                {"weight": 7.0},
                {"pct": 0.05},
            ],
        })
        self.assertEqual(row["fund_total_assets"], 5_000_000_000)
        self.assertEqual(row["fund_top10_weight_pct"], 20.0)
        self.assertNotIn("top_holdings", row)

    def test_columnar_startup_budget_is_production_grade(self):
        self.assertEqual(shards.MAX_COLUMNAR_BYTES, 2_250_000)
        self.assertEqual(shards.MAX_COLUMNAR_INDEX_RATIO, 0.35)
        self.assertLess(shards.MAX_COLUMNAR_BYTES, shards.MAX_INDEX_BYTES)
        self.assertLess(shards.MAX_COLUMNAR_INDEX_RATIO, 0.5)

    def test_columnar_pack_round_trips_sparse_rows(self):
        payload = {
            "schema_version": 521,
            "generated_at": "2026-09-05T15:09:55Z",
            "stocks": [
                {"ticker": "MSFT", "score": 88.0, "currency": "USD"},
                {"ticker": "AIR.PA", "score": 79.0, "currency": "EUR", "fund_ucits": True},
            ],
        }
        packed = shards.pack_index_payload(payload)
        self.assertEqual(packed["layout"], "field_rows_v1")
        unpacked = shards.unpack_index_payload(packed)
        self.assertEqual(unpacked["stocks"], payload["stocks"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
