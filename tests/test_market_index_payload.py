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

    def test_portfolio_sector_payload_keeps_only_classification_identity(self):
        row = shards.portfolio_sector_row({
            "ticker": "NESN.SW",
            "sector": "Consumer Defensive",
            "industry": "Packaged Foods",
            "quote_type": "EQUITY",
            "score": 43,
            "thesis_summary": "must stay out",
        })
        self.assertEqual(row, {
            "sector": "Consumer Defensive",
            "industry": "Packaged Foods",
            "quote_type": "EQUITY",
        })
        self.assertIsNone(shards.portfolio_sector_row({"ticker": "UNKNOWN"}))

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

    def test_zombie_risk_diagnostics_survive_startup_index(self):
        row = shards.index_row({
            "ticker": "ZMB",
            "zombie": "yes",
            "zombie_risk_state": "probable",
            "zombie_risk_years": 3,
            "zombie_risk_reason": "EBIT não cobre juros há 3 exercícios consecutivos.",
            "annual_zombie_history": [{"date": "2025-12-31", "ebit": 5, "interest_expense": 10}],
        })
        self.assertEqual(row["zombie"], "yes")
        self.assertEqual(row["zombie_risk_state"], "probable")
        self.assertEqual(row["zombie_risk_years"], 3)
        self.assertIn("zombie_risk_state", shards.INDEX_KEYS)
        self.assertIn("zombie_risk_years", shards.INDEX_KEYS)
        self.assertNotIn("zombie_risk_reason", shards.INDEX_KEYS)
        self.assertNotIn("annual_zombie_history", shards.INDEX_KEYS)
        self.assertNotIn("zombie_risk_reason", row)
        self.assertNotIn("annual_zombie_history", row)


    def test_raw_score_reaches_startup_for_conviction_without_replacing_public_score(self):
        row = shards.index_row({
            "ticker": "TEST",
            "score": 59.0,
            "score_raw": 82.0,
            "confidence_score": 58.0,
            "score_reliability": "limited_evidence",
        })
        self.assertEqual(row["score"], 59.0)
        self.assertEqual(row["score_raw"], 82.0)
        self.assertIn("score_raw", shards.INDEX_KEYS)

    def test_columnar_startup_budget_is_production_grade(self):
        self.assertEqual(shards.MAX_COLUMNAR_BYTES, 2_250_000)
        self.assertEqual(shards.MAX_COLUMNAR_INDEX_RATIO, 0.35)
        self.assertLess(shards.MAX_COLUMNAR_BYTES, shards.MAX_INDEX_BYTES)
        self.assertLess(shards.MAX_COLUMNAR_INDEX_RATIO, 0.5)

    def test_lossless_dictionary_codec_saves_more_than_recent_budget_overage(self):
        import json
        rows = [
            {"ticker": f"TEST{i:04d}",
             "risk_gate": "unknown" if i % 3 == 0 else "restricted",
             "sector": "Information Technology" if i % 2 else "Consumer Defensive",
             "market_cap": 100_000_000_000 + i,
             "insider_buy_value_30d": None if i % 2 else 123,
             "score": 72.3456789,
             "confidence_label": "low confidence" if i % 2 else "moderate confidence"}
            for i in range(1200)
        ]
        payload = {"schema_version": 3, "generated_at": "2026-11-08", "stocks": rows}
        packed = shards.pack_index_payload(payload)
        self.assertEqual(packed["layout"], "field_rows_v2")
        self.assertTrue(packed["string_dictionaries"])
        unpacked = shards.unpack_index_payload(packed)
        self.assertEqual(unpacked["stocks"], rows)
        self.assertEqual(unpacked["generated_at"], "2026-11-08")
        # Compare the real JSON wire bytes with the same v1 fields/rows without
        # categorical coding; do not infer savings from gzip or semantic drops.
        old_rows = [[row.get(field) for field in packed["fields"]] for row in rows]
        for row in old_rows:
            while row and row[-1] is None:
                row.pop()
        old_wire = {**payload, "layout": "field_rows_v1",
                    "fields": packed["fields"], "rows": old_rows}
        del old_wire["stocks"]
        old_bytes = len(json.dumps(old_wire, ensure_ascii=False, separators=(",", ":")).encode())
        new_bytes = len(json.dumps(packed, ensure_ascii=False, separators=(",", ":")).encode())
        self.assertGreater(old_bytes - new_bytes, 9250)
        self.assertLess(new_bytes, old_bytes)

    def test_v2_rejects_broken_string_dictionary_codes(self):
        sample = [{"ticker": f"T{i}", "risk_gate": "unknown"} for i in range(300)]
        packed = shards.pack_index_payload({"stocks": sample})
        self.assertEqual(packed["layout"], "field_rows_v2")
        field_index = str(packed["fields"].index("risk_gate"))
        packed["rows"][0][int(field_index)] = -1
        with self.assertRaisesRegex(ValueError, "invalid categorical code"):
            shards.unpack_index_payload(packed)

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
