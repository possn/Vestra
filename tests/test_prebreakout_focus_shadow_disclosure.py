import importlib.util
import unittest
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("scanner",ROOT/"scripts/refresh_prebreakout_scanner.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class FocusShadowDisclosureTests(unittest.TestCase):
 def candidate(self,position):
  return {"ticker":"EZJ.L","date":"2026-10-27","stage":"pré-breakout",
   "source":"yahoo:daily_ohlcv","score":79,"distancePct":0.75,
   "vcpConfirmed":True,"volumeConfirmed":False,"volumeDry":True,
   "quantitativeDiagnostics":{"atrContractionRatio":0.577,
      "baseSupportRetention10":1.0,"basePositionPct":position}}
 def test_focus_can_disclose_stricter_structural_rejection_without_reranking(self):
  focus=mod.daily_focus([self.candidate(76.4)],date(2026,10,28))
  self.assertEqual(focus["ticker"],"EZJ.L")
  self.assertEqual(focus["selection_tier"],"verified_prebreakout")
  self.assertEqual(focus["structural_readiness_shadow"]["status"],"research_rejected")
  self.assertFalse(focus["structural_readiness_shadow"]["eligible"])
  self.assertIsNone(focus["success_probability"])
 def test_clear_diagnostics_only_change_shadow_research(self):
  focus=mod.daily_focus([self.candidate(85)],date(2026,10,28))
  self.assertTrue(focus["structural_readiness_shadow"]["eligible"])
  self.assertEqual(focus["technical_score"],79)
 def test_missing_diagnostic_is_unknown_not_cleared(self):
  row=self.candidate(85);del row["quantitativeDiagnostics"]["atrContractionRatio"]
  focus=mod.daily_focus([row],date(2026,10,28))
  self.assertEqual(focus["structural_readiness_shadow"]["status"],"unverifiable")
  self.assertIsNone(focus["structural_readiness_shadow"]["eligible"])
if __name__=="__main__":unittest.main()
