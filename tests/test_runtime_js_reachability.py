from contextlib import redirect_stdout
from io import StringIO
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
        self.assertEqual(report['special'].get('worker-router.js'), 'cloudflare_worker')
        self.assertEqual(report['special'].get('worker.js'), 'cloudflare_worker_module')

    def test_no_unreferenced_top_level_runtime_scripts_remain(self):
        report = audit.build_report()
        self.assertEqual(report['unreferenced'], [])

    def test_arbitrary_js_string_is_not_a_runtime_edge(self):
        refs = audit.runtime_refs("const note = 'ghost-runtime.js';")
        self.assertEqual(refs, [])

    def test_explicit_script_loaders_and_imports_are_runtime_edges(self):
        text = """
        script.src = 'dynamic-a.js?v=2';
        loadScript('runtime-id', 'dynamic-b.js?v=1', window.Ready);
        import worker from './dynamic-c.js';
        import('./dynamic-d.js');
        """
        self.assertEqual(
            audit.runtime_refs(text),
            ['dynamic-a.js', 'dynamic-b.js', 'dynamic-c.js', 'dynamic-d.js'],
        )

    def test_audit_fails_closed_when_an_orphan_is_reported(self):
        original = audit.build_report
        try:
            audit.build_report = lambda: {'missing_direct': [], 'unreferenced': ['orphan.js']}
            with redirect_stdout(StringIO()):
                self.assertEqual(audit.main(), 1)
        finally:
            audit.build_report = original

    def test_audit_never_deletes_unreferenced_scripts(self):
        text = AUDIT_PATH.read_text(encoding='utf-8')
        self.assertNotIn('.unlink(', text)
        self.assertNotIn('os.remove(', text)
        self.assertIn('unreferenced', text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
