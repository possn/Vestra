from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.js").read_text(encoding="utf-8")
CORE = (ROOT / "app-broker-parsing-core.js").read_text(encoding="utf-8")
PARSERS = (ROOT / "app-broker-parsers.js").read_text(encoding="utf-8")
WORKBOOK = (ROOT / "app-broker-workbook.js").read_text(encoding="utf-8")


class BrokerRealExportRegressionTests(unittest.TestCase):
    def test_xtb_open_positions_use_exact_eur_controls(self):
        self.assertIn("r.current_price", PARSERS)
        self.assertIn("reportedValueEUR", PARSERS)
        self.assertIn("reportedNetProfitEUR", PARSERS)
        self.assertIn("reportedValueEUR - reportedNetProfitEUR", PARSERS)
        self.assertIn("lotMktVal = reportedValueEUR", PARSERS)

    def test_xtb_snapshot_accepts_iso_datetime_from_sheetjs(self):
        self.assertIn("const iso = s.match", WORKBOOK)
        self.assertIn("if (iso) return `${iso[1]}-${iso[2]}-${iso[3]}`", WORKBOOK)
        self.assertIn("data as of report generated|date to", WORKBOOK)

    def test_t212_corporate_actions_are_not_silently_dropped(self):
        self.assertIn('n.includes("stock acquisition")', CORE)
        self.assertIn('n.includes("result adjustment")', CORE)
        self.assertIn('if (e.type === "CASH_ADJUSTMENT")', APP)
        self.assertIn('category: "Ajuste corretora"', APP)

    def test_newer_broker_reports_replace_contained_older_sources(self):
        self.assertIn("function removeSupersededBrokerSources", APP)
        self.assertIn("range.firstDate <= oldRange.firstDate", APP)
        self.assertIn("range.lastDate >= oldRange.lastDate", APP)
        self.assertIn("logicalReplaced", APP)
        self.assertIn("bd.events = (bd.events || []).filter", APP)
        self.assertIn("bd.positions = (bd.positions || []).filter", APP)

    def test_current_t212_from_export_is_not_left_as_generic_csv(self):
        self.assertIn("function inferBrokerFromParsedImport", APP)
        self.assertIn('looksT212 ? "Trading 212" : named', APP)
        self.assertIn('oldBroker === "Corretora CSV"', APP)
        self.assertIn('/^from_/i.test', APP)


if __name__ == "__main__":
    unittest.main(verbosity=2)
