from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.js").read_text(encoding="utf-8")


class XtbDividendRebuildIdempotenceTests(unittest.TestCase):
    def test_rebuild_clones_raw_broker_events_before_annotation(self):
        self.assertIn(
            'let events = (bd.events || []).map(e => (e && typeof e === "object" ? { ...e } : e)).sort(',
            APP,
        )
        self.assertNotIn(
            'let events = (bd.events || []).slice().sort(',
            APP,
        )

    def test_paired_xtb_withholding_replaces_working_tax_instead_of_accumulating(self):
        self.assertIn('e.taxEUR = wht;', APP)
        self.assertNotIn('e.taxEUR = (parseNum(e.taxEUR) || 0) + wht;', APP)
        self.assertIn('XTB "Amount" on the Dividend row is already GROSS; only attach the tax.', APP)

    def test_t212_direct_tax_semantics_are_not_changed(self):
        self.assertIn('T212 "Total" is the GROSS amount in EUR, NOT net of withholding tax.', APP)
        self.assertIn('XTB: "Amount" for Dividend is also gross', APP)


if __name__ == "__main__":
    unittest.main(verbosity=2)
