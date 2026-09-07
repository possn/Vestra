from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PARSER = (ROOT / "app-broker-parsers.js").read_text(encoding="utf-8")
NORM = (ROOT / "app-broker-normalization.js").read_text(encoding="utf-8")
APP = (ROOT / "app.js").read_text(encoding="utf-8")


class XtbWithholdingSignedCorrectionTests(unittest.TestCase):
    def test_xtb_parser_preserves_wht_reversal_sign(self):
        self.assertIn("evt.taxEUR = -amount;", PARSER)
        self.assertIn("evt.resultEUR = amount;", PARSER)
        self.assertNotIn("evt.taxEUR = Math.abs(amount);", PARSER)

    def test_negative_dividend_correction_can_pair_with_positive_wht_reversal(self):
        self.assertIn('e.type === "DIVIDEND_ADJ" && parseNum(e.totalEUR) < 0', APP)
        self.assertIn('parseNum(a.taxEUR) !== 0 && parseNum(a.totalEUR) === 0', APP)

    def test_dividend_adjustment_tax_is_signed_end_to_end(self):
        self.assertIn("function divTax(d, v)", NORM)
        self.assertIn('(d && d.isAdjustment) ? tax : Math.max(0, tax)', NORM)
        self.assertIn('e.type === "DIVIDEND_ADJ" ? parseNum(e.taxEUR)', NORM)
        self.assertIn('r.storedTax += divTax(d, d.taxWithheld);', NORM)
        self.assertIn('e.type === "DIVIDEND_ADJ" ? parseNum(e.taxEUR)', APP)

    def test_orphan_wht_can_reduce_existing_tax_without_going_negative(self):
        self.assertIn('Math.abs(whtTotal) < 1e-9', APP)
        self.assertIn('const adjustedTax = parseNum(d.taxWithheld) + share;', APP)
        self.assertIn('Math.max(0, Math.min(parseNum(d.grossAmount), adjustedTax))', APP)

    def test_previous_idempotence_fix_remains(self):
        self.assertIn('let events = (bd.events || []).map(e => (e && typeof e === "object" ? { ...e } : e)).sort(', APP)
        self.assertIn('e.taxEUR = wht;', APP)


if __name__ == "__main__":
    unittest.main(verbosity=2)
