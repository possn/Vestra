"""The prior-impulse diagnostic is observational, not a new live gate."""
import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("prebreakout",ROOT/"scripts/refresh_prebreakout_scanner.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class PrebaseContextTests(unittest.TestCase):
    def test_context_is_asof_and_does_not_change_stage(self):
        import sys
        sys.path.insert(0,str(ROOT/"tests"))
        from test_refresh_prebreakout_scanner import PrebreakoutDataTests
        rows=PrebreakoutDataTests().bars()
        row=mod.scan_bars("TEST",rows)
        self.assertIsNotNone(row)
        q=row["quantitativeDiagnostics"]
        self.assertEqual(q["preBaseContext"],"research_only_fixed_closed_bars_no_ranking_gate")
        self.assertEqual(len(q["contractionWidths20Pct"]),3)
        self.assertAlmostEqual(q["preBaseReturn40Pct"],round((rows[-40]["close"]/rows[-80]["close"]-1)*100,2))
        hi=max(b["high"] for b in rows[-80:-40]);lo=min(b["low"] for b in rows[-80:-40])
        self.assertAlmostEqual(q["preBaseRange40Pct"],round((hi/lo-1)*100,2))
        self.assertTrue(row["vcpConfirmed"])
        self.assertIn(row["stage"],("pré-breakout","compressão"))
if __name__=="__main__":
    unittest.main()
