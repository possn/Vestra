from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTICS = (ROOT / 'portfolio-diagnostics.js').read_text(encoding='utf-8')


class BrokerWithholdingIntegrityTests(unittest.TestCase):
    def test_xtb_dividend_tax_is_repaired_only_when_separate_wht_rows_exist(self):
        self.assertIn("e.type!=='DIVIDEND_ADJ'", DIAGNOSTICS)
        self.assertIn("num(e.taxEUR)>0&&num(e.totalEUR)===0", DIAGNOSTICS)
        self.assertIn("e.type!=='DIVIDEND'", DIAGNOSTICS)
        self.assertIn("!whtSources.has(sourceKey(e))", DIAGNOSTICS)
        self.assertIn("e.taxEUR=0", DIAGNOSTICS)
        self.assertIn("/\\bXTB\\b/i", DIAGNOSTICS)

    def test_rebuild_never_mutates_persisted_broker_event_objects(self):
        self.assertIn("const rawEvents=bd.events", DIAGNOSTICS)
        self.assertIn("bd.events=rawEvents.map(e=>e&&typeof e==='object'?{...e}:e)", DIAGNOSTICS)
        self.assertIn("finally{bd.events=rawEvents;}", DIAGNOSTICS)
        self.assertLess(
            DIAGNOSTICS.index("bd.events=rawEvents.map"),
            DIAGNOSTICS.index("originalRebuild.apply(this,args)"),
        )

    def test_existing_devices_are_forced_through_one_clean_rebuild(self):
        self.assertIn("BROKER_WHT_INTEGRITY_VERSION=1", DIAGNOSTICS)
        self.assertIn("brokerWhtIntegrityVersion", DIAGNOSTICS)
        self.assertIn("loaded.settings.brokerRebuildSchemaVersion=0", DIAGNOSTICS)
        self.assertIn("loadStateAsync=async function", DIAGNOSTICS)
        self.assertIn("rebuildBrokerGeneratedData=function", DIAGNOSTICS)

    def test_repeated_wht_annotations_are_removed_before_regeneration(self):
        self.assertIn("/WHT:/i.test(notes)", DIAGNOSTICS)
        self.assertIn("replace(/(?:\\s*·\\s*)?WHT:", DIAGNOSTICS)


if __name__ == '__main__':
    unittest.main(verbosity=2)
