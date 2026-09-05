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
        self.assertEqual(row["dossier_shard"], "A")

    def test_scanner_results_remain_available_before_dossier_hydration(self):
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
        row = shards.index_row({"ticker": "MSFT", "scanner_results": scanner_results})
        self.assertEqual(row["scanner_results"], scanner_results)

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
