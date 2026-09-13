from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "architecture-invariants.yml"


class ArchitecturePythonCoverageTests(unittest.TestCase):
    def test_architecture_gate_watches_all_python_scripts(self):
        src = WORKFLOW.read_text(encoding="utf-8")
        self.assertGreaterEqual(src.count("- 'scripts/**'"), 2)

    def test_architecture_gate_compiles_scripts_dynamically(self):
        src = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python -m compileall -q scripts tests", src)
        self.assertNotIn("python -m py_compile scripts/run.py", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
