import importlib.util
import unittest
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("guard",ROOT/"scripts/defer_main_publish_if_code_pr.py")
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)

class MacroPublishGraceTests(unittest.TestCase):
 def at(self,h,m):return datetime(2026,10,29,h,m,tzinfo=timezone.utc)
 def prior(self,stamp):return {"generated_at":stamp}
 def test_recent_published_feed_can_defer(self):
  self.assertFalse(guard.macro_publication_overdue(self.prior("2026-10-29T07:00:00Z"),self.at(8,30),4))
 def test_older_than_four_hours_cannot_defer_indefinitely(self):
  self.assertTrue(guard.macro_publication_overdue(self.prior("2026-10-29T03:00:00Z"),self.at(8,30),4))
 def test_missing_provenance_fails_open_to_fresh_data_publication(self):
  self.assertTrue(guard.macro_publication_overdue({},self.at(8,30),4))
 def test_invalid_arguments(self):
  with self.assertRaises(ValueError):guard.macro_publication_overdue({},self.at(8,30),0)
  with self.assertRaises(ValueError):guard.macro_publication_overdue({},datetime(2026,10,29,8,30),4)
 def test_macro_workflow_uses_previous_publication(self):
  s=(ROOT/".github/workflows/update-macro-events.yml").read_text()
  self.assertIn("python scripts/defer_main_publish_if_code_pr.py --macro-max-staleness-hours 4",s)
  self.assertIn("VESTRA_MACRO_PREVIOUS: /tmp/vestra-macro-events-previous.json",s)

if __name__=="__main__":unittest.main()
