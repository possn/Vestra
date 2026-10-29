import importlib.util
import unittest
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("guard",ROOT/"scripts/defer_main_publish_if_code_pr.py")
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)

class MacroPublishGraceTests(unittest.TestCase):
 def at(self,h,m):return datetime(2026,10,29,h,m,tzinfo=timezone.utc)
 def test_short_window_after_hourly_cron(self):
  self.assertFalse(guard.macro_grace_expired(self.at(8,20),15))
  self.assertFalse(guard.macro_grace_expired(self.at(8,34),15))
  self.assertTrue(guard.macro_grace_expired(self.at(8,35),15))
  self.assertTrue(guard.macro_grace_expired(self.at(9,5),15))
 def test_invalid_inputs_fail_closed(self):
  with self.assertRaises(ValueError):guard.macro_grace_expired(self.at(8,35),60)
  with self.assertRaises(ValueError):guard.macro_grace_expired(datetime(2026,10,29,8,35),15)
 def test_macro_workflow_uses_bounded_grace(self):
  s=(ROOT/".github/workflows/update-macro-events.yml").read_text()
  self.assertIn("python scripts/defer_main_publish_if_code_pr.py --macro-grace-minutes 15",s)
  self.assertIn('cron: "20 * * * *"',s)

if __name__=="__main__":unittest.main()
