import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("check_transitions",ROOT/"scripts/check_prebreakout_transitions.py")
import sys
sys.path.insert(0,str(ROOT/"scripts"))
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class TransitionPublicationTests(unittest.TestCase):
    def test_publication_matches_archives_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);slots=root/"data"/"prebreakout-history"/"2026"/"slots"
            slots.mkdir(parents=True)
            source={"schema":"vestra_prebreakout_v1","generated_at":"2026-10-15T14:10:00Z",
                "scan_slot_utc":2,"signals":[{"ticker":"AAA","stage":"compressão",
                    "score":60,"date":"2026-10-15","source":"yahoo:daily_ohlcv"}]}
            (slots/"2026-10-15-slot2.json").write_text(json.dumps(source))
            from build_prebreakout_transitions import build
            original=build(root/"data"/"prebreakout-history")
            output=root/"data"/"prebreakout-transitions.json"
            output.write_text(json.dumps(original))
            self.assertEqual(mod.verify(root)["events"],1)
            altered=dict(original)
            altered["events"]=[]
            output.write_text(json.dumps(altered))
            with self.assertRaises(ValueError):mod.verify(root)
            altered=dict(original);altered["historical_only"]=False
            output.write_text(json.dumps(altered))
            with self.assertRaises(ValueError):mod.verify(root)

if __name__=="__main__":
    unittest.main()
