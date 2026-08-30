from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / 'scripts' / 'runtime_js_audit.py'

spec = importlib.util.spec_from_file_location('runtime_js_audit', AUDIT_PATH)
audit = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(audit)


class RuntimeJsReachabilityTests(unittest.TestCase):
    def test_direct_script_entries_exist(self):
        report = audit.build_report()
        self.assertFalse(report['missing_direct'], report['missing_direct'])

    def test_model_validation_is_reachable_dynamically(self):
        report = audit.build_report()
        self.assertIn('market-company-brief.js', report['direct'])
        self.assertIn('market-model-validation.js', report['dynamic'])

    def test_worker_entrypoints_are_classified_separately(self):
        report = audit.build_report()
        self.assertEqual(report['special'].get('sw.js'), 'service_worker')
        self.assertEqual(report['special'].get('worker.js'), 'cloudflare_worker')

    def test_no_unreferenced_top_level_runtime_scripts_remain(self):
        report = audit.build_report()
        self.assertEqual(report['unreferenced'], [])

    def test_audit_never_deletes_unreferenced_scripts(self):
        text = AUDIT_PATH.read_text(encoding='utf-8')
        self.assertNotIn('.unlink(', text)
        self.assertNotIn('os.remove(', text)
        self.assertIn('unreferenced', text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
