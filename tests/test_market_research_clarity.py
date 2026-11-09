"""Market research must not expose duplicate technical lenses or misleading scanner scores."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

def source(name):
    return (ROOT / name).read_text(encoding="utf-8")

class MarketResearchClarityTests(unittest.TestCase):
    def test_breakout_lab_is_not_mislabeled_general_scanner(self):
        html = source("index.html")
        self.assertIn('data-market-tool="scanner" aria-label="Abrir scanner de estratégias de investimento"', html)
        self.assertIn("<strong>Estratégias</strong>", html)
        self.assertNotIn("<strong>Breakout Lab</strong>", html)
        self.assertIn('data-market-mode="smart"', html)

    def test_single_canonical_prebreakout_and_smallcap_controls(self):
        lenses = source("market-opportunity-lenses.js")
        ranked = source("market-opportunities.js")
        self.assertEqual(lenses.count('data-vestra-lens="breakout"'), 1)
        self.assertEqual(lenses.count('data-vestra-lens="smallcap_breakout"'), 1)
        self.assertNotIn("createElement('button');smallcapChip", ranked)
        self.assertNotIn("row.append(normal,smallcapChip)", ranked)
        self.assertIn("section.querySelector('.vestra-technical-lenses')?.remove()", ranked)
        self.assertIn("window.VestraMarketOpportunities?.selectLens?.(activeLens,moreSectorValue())", lenses)

    def test_scanner_does_not_display_unrelated_vestra_score_as_strategy_score(self):
        runtime = source("market-analysis-tools-runtime.js")
        self.assertIn("return stockRow(stock, meta, num(r?.score))", runtime)
        self.assertIn("scannerScore === undefined ? num(stock?.score) : num(scannerScore)", runtime)
        self.assertIn("Score Scanner", runtime)

    def test_company_activity_is_explicit_and_never_invented(self):
        ranked = source("market-opportunities.js")
        runtime = source("market-analysis-tools-runtime.js")
        self.assertIn("long_business_summary", ranked)
        self.assertIn("business_description", runtime)
        self.assertIn("Atividade por descrever", ranked)
        self.assertIn("Atividade ainda não descrita nos dados disponíveis.", runtime)

    def test_company_summaries_are_source_derived_and_bounded_for_iphone(self):
        from scripts.build_market_shards import index_row
        long = "Esta empresa desenvolve infraestruturas de energia renovável e redes de distribuição, com atividades operacionais em vários países europeus." * 3
        row = {"ticker": "TEST", "quote_type": "EQUITY", "long_business_summary": long}
        compact = index_row(row)
        self.assertIn("business_summary", compact)
        self.assertTrue(compact["business_summary"].startswith("Esta empresa"))
        self.assertLessEqual(len(compact["business_summary"]), 105)
        self.assertNotIn("long_business_summary", compact)
        self.assertNotIn("business_summary", index_row({"ticker": "NONE", "quote_type": "EQUITY", "industry": "Utilities"}))
        self.assertNotIn("business_summary", index_row({"ticker": "ETF", "quote_type": "ETF", "business_summary": long}))

    def test_provider_name_placeholder_is_not_a_business_description(self):
        from scripts.build_market_shards import index_row
        name = "Agilent Technologies, Inc."
        row = {"ticker": "A", "name": name, "quote_type": "EQUITY",
               "long_business_summary": "Agilent Technologies, Inc.",
               "business_summary": "Agilent Technologies, Inc.",
               "description": "Designs, develops and supplies laboratory instruments and analytical software worldwide."}
        output = index_row(row)
        self.assertIn("Designs, develops", output["business_summary"])
        row.pop("description")
        self.assertNotIn("business_summary", index_row(row))
        row["long_business_summary"] = (
            "Agilent Technologies, Inc. manufactures and sells analytical instruments "
            "for clinical and industrial laboratories."
        )
        self.assertIn("manufactures and sells", index_row(row)["business_summary"])

    def test_projected_company_activity_preserves_real_mobile_startup_budget(self):
        import json
        from scripts import build_market_shards as builder
        source = json.loads((ROOT / "data/stocks.json").read_text(encoding="utf-8"))
        index = json.loads((ROOT / "data/stocks-index.json").read_text(encoding="utf-8"))
        descriptions = {}
        for item in source.get("stocks", []):
            if isinstance(item, dict) and item.get("ticker"):
                brief = builder.index_row(item).get("business_summary")
                if brief:
                    descriptions[str(item["ticker"]).upper()] = brief
        for item in index["stocks"]:
            snippet = descriptions.get(str(item.get("ticker") or "").upper())
            if snippet:
                item["business_summary"] = snippet
        packed = builder.pack_index_payload(index)
        encoded = len(json.dumps(packed, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        legacy = len(json.dumps(index, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        self.assertLessEqual(encoded, builder.MAX_COLUMNAR_BYTES)
        self.assertLessEqual(legacy, builder.MAX_INDEX_HARD_BYTES)

if __name__ == "__main__":
    unittest.main()
