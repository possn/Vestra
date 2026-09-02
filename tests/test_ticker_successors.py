from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import ticker_successors


class TickerSuccessorContractTests(unittest.TestCase):
    def test_exact_successors_are_source_backed(self):
        expected = {
            "BITF": ("KEEL", "2026-04-06"),
            "IINN": ("QTEX", "2026-05-20"),
        }
        self.assertEqual(set(ticker_successors.TICKER_SUCCESSORS), set(expected))
        for old, (new, date) in expected.items():
            row = ticker_successors.successor_for(old.lower())
            self.assertEqual(row["successor"], new)
            self.assertEqual(row["effective_date"], date)
            self.assertTrue(row["source"])
            self.assertEqual(ticker_successors.retrieval_symbol(old), new)
        self.assertIsNone(ticker_successors.successor_for("MSFT"))
        self.assertEqual(ticker_successors.retrieval_symbol("MSFT"), "MSFT")

    def test_python_fetch_preserves_historical_ticker_and_records_retrieval_ticker(self):
        source = (SCRIPTS / "fundamentals.py").read_text(encoding="utf-8")
        self.assertIn("from ticker_successors import successor_for, retrieval_symbol", source)
        self.assertIn("retrieval_ticker: str | None = None", source)
        self.assertIn("ticker_successor_effective_date: str | None = None", source)
        self.assertIn("ticker_successor_source: str | None = None", source)
        self.assertIn("m = RawMetrics(ticker=ticker)", source)
        self.assertIn("m.retrieval_ticker = yahoo_symbol", source)
        self.assertIn("t = retrieval_symbol(ticker)", source)

    def test_worker_preserves_requested_key_but_retrieves_successor(self):
        source = (ROOT / "worker.js").read_text(encoding="utf-8")
        self.assertIn('"BITF": { ticker: "KEEL", effective_date: "2026-04-06" }', source)
        self.assertIn('"IINN": { ticker: "QTEX", effective_date: "2026-05-20" }', source)
        self.assertIn("ticker: raw", source)
        self.assertIn("retrieval_ticker: canonical", source)
        self.assertIn("out[tickers[i]]", source)
        self.assertNotIn('"BITF": "KEEL"', source)
        self.assertNotIn('"IINN": "QTEX"', source)

    def test_market_dossier_preserves_requested_ticker_and_successor_provenance(self):
        source = (ROOT / "worker.js").read_text(encoding="utf-8")
        self.assertIn("const requested = String(ticker || '').trim().toUpperCase();", source)
        self.assertIn("const successor = successorMetadata(requested);", source)
        self.assertIn("ticker: successor ? requested : canonical", source)
        self.assertIn("retrieval_ticker: successor ? canonical : null", source)
        self.assertIn("ticker_successor_effective_date: successor?.effective_date || null", source)
        self.assertIn("data.ticker = requested", source)
        self.assertIn("data.retrieval_ticker = canonical", source)

    def test_historical_portfolio_symbols_are_not_rewritten_in_extra_universe(self):
        extra = (ROOT / "data" / "extra_tickers.json").read_text(encoding="utf-8")
        self.assertIn('"BITF"', extra)
        self.assertIn('"IINN"', extra)


if __name__ == "__main__":
    unittest.main(verbosity=2)
