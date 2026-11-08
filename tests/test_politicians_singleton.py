"""Verify that duplicated WebKit script loading cannot double-register politician UI."""
from pathlib import Path
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]


class PoliticiansSingletonTests(unittest.TestCase):
    def test_double_injected_module_registers_once(self):
        result=subprocess.run(
            ["node",str(ROOT/"tests/runtime_politicians_singleton_contract.js")],
            cwd=ROOT,capture_output=True,text=True,timeout=15,check=False)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn("politicians double-injection singleton: ok",result.stdout)


if __name__=="__main__":
    unittest.main()
