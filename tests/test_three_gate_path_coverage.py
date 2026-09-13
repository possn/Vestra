from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ThreeGatePathCoverageTests(unittest.TestCase):
    def test_python_pipeline_changes_trigger_browser_and_runtime_gates(self):
        browser = (ROOT / '.github' / 'workflows' / 'browser-e2e.yml').read_text(encoding='utf-8')
        runtime = (ROOT / '.github' / 'workflows' / 'runtime-js-syntax.yml').read_text(encoding='utf-8')
        for workflow in (browser, runtime):
            self.assertIn("- 'scripts/**'", workflow)
            self.assertIn("- 'tests/**/*.py'", workflow)


if __name__ == '__main__':
    unittest.main(verbosity=2)
