"""Exercise the market iPhone startup decoder on a real Node runtime."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MarketColumnDictionaryBrowserTests(unittest.TestCase):
    def test_browser_decodes_financial_fields_losslessly(self):
        proc = subprocess.run(
            ["node", str(ROOT/"tests/runtime_market_column_dictionaries.js")],
            cwd=ROOT, capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(proc.returncode, 0, proc.stdout+proc.stderr)
        self.assertIn("market column dictionary browser contract: ok", proc.stdout)


if __name__ == "__main__":
    unittest.main()
