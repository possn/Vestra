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


if __name__ == "__main__":
    unittest.main(verbosity=2)
