import importlib.util
import unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("macro",ROOT/"scripts/audit_macro_publication.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
NOW=datetime(2026,10,29,8,tzinfo=timezone.utc)
def sample(stamp):
    return {"schema_version":2,"generated_at":stamp,
        "source_status":{source:{"state":"fresh"} for source in mod.SOURCES},
        "events":[{"importance":"critical","short_title":"FOMC"}]}
class PublicationAuditTests(unittest.TestCase):
    def test_stale_calendar_not_masked_by_upcoming_fomc(self):
        report=mod.audit(sample("2026-10-12T15:28:12Z"),NOW)
        self.assertTrue(report["refresh_needed"]);self.assertFalse(report["publication_fresh"])
        self.assertEqual(report["critical_events_present"],1)
    def test_recent_calendar_with_fallback_source_is_transparent(self):
        data=sample("2026-10-29T07:00:00Z");data["source_status"]["fed"]["state"]="fallback"
        report=mod.audit(data,NOW)
        self.assertFalse(report["refresh_needed"])
        self.assertEqual(report["source_status"]["fed"],"fallback")
    def test_missing_source_never_passes(self):
        data=sample("2026-10-29T07:00:00Z");del data["source_status"]["fed"]
        self.assertTrue(mod.audit(data,NOW)["refresh_needed"])
    def test_future_date_rejected(self):
        with self.assertRaisesRegex(ValueError,"future-dated"):
            mod.audit(sample("2026-11-01T00:00:00Z"),NOW)
if __name__=="__main__":unittest.main()
