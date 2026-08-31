from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/verify_learned_universe_deployment.py'
WORKFLOW = ROOT / '.github/workflows/verify-cloudflare-worker.yml'


class LearnedUniverseProductionContractTests(unittest.TestCase):
    def test_verifier_is_valid_python(self):
        subprocess.run(['python', '-m', 'py_compile', str(SCRIPT)], check=True, cwd=ROOT)

    def test_verifier_requires_router_storage_and_endpoint(self):
        text = SCRIPT.read_text(encoding='utf-8')
        self.assertIn('learned_universe', text)
        self.assertIn('learned_universe_storage', text)
        self.assertIn('durable_object', text)
        self.assertIn('/learned-universe', text)
        self.assertIn('schema_version', text)
        self.assertIn('Access-Control-Allow-Origin', text)

    def test_main_verifier_retries_until_both_contracts_are_live(self):
        text = WORKFLOW.read_text(encoding='utf-8')
        self.assertIn('scripts/verify_learned_universe_deployment.py', text)
        self.assertIn('&& python scripts/verify_learned_universe_deployment.py', text)
        self.assertIn('for attempt in 1 2 3 4 5', text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
