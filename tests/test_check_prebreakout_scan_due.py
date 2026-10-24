import importlib.util
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("due", ROOT/"scripts/check_prebreakout_scan_due.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class DueContract(unittest.TestCase):
    def at(self,hour,minute=35,day=15):
        return datetime(2026,10,day,hour,minute,tzinfo=timezone.utc)

    def test_real_retry_only_after_scheduled_slot(self):
        with tempfile.TemporaryDirectory() as directory:
            archive=Path(directory)
            self.assertFalse(mod.should_scan(self.at(20,9),archive))
            self.assertTrue(mod.should_scan(self.at(20,10),archive))
            self.assertTrue(mod.should_scan(self.at(21),archive))
            self.assertTrue(mod.should_scan(self.at(23),archive))
            self.assertFalse(mod.should_scan(self.at(18),archive))
            self.assertFalse(mod.should_scan(self.at(0),archive))

    def test_immutable_slot_never_republished(self):
        with tempfile.TemporaryDirectory() as directory:
            archive=Path(directory)
            path=archive/"2026"/"slots"/"2026-10-15-slot3.json"
            path.parent.mkdir(parents=True)
            path.write_text("{}")
            self.assertFalse(mod.should_scan(self.at(21),archive))
            self.assertFalse(mod.should_scan(self.at(23),archive))

    def test_saturday_catchup_publishes_friday_complete_close_only(self):
        with tempfile.TemporaryDirectory() as directory:
            archive=Path(directory)
            self.assertFalse(mod.should_scan(self.at(2,9,day=17),archive))
            self.assertTrue(mod.should_scan(self.at(2,10,day=17),archive))
            self.assertTrue(mod.should_scan(self.at(5,day=17),archive))
            self.assertFalse(mod.should_scan(self.at(8,day=17),archive))
            self.assertFalse(mod.should_scan(self.at(2,day=18),archive))
            done=archive/'2026'/'slots'/'2026-10-17-slot0.json'
            done.parent.mkdir(parents=True)
            done.write_text('{}')
            self.assertFalse(mod.should_scan(self.at(3,day=17),archive))

    def test_naive_clock_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                mod.should_scan(datetime(2026,10,15,21,35),Path(directory))

if __name__=="__main__":
    unittest.main()
