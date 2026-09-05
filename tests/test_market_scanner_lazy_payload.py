import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MarketScannerLazyPayloadTests(unittest.TestCase):
    def test_runtime_contract(self):
        subprocess.run(
            ["node", "tests/runtime_market_scanner_data_contract.js"],
            cwd=ROOT,
            check=True,
        )

    def test_dynamic_module_is_reachable_from_market_shell(self):
        shell = (ROOT / "market-static-universe.js").read_text(encoding="utf-8")
        module = (ROOT / "market-scanner-data.js").read_text(encoding="utf-8")
        self.assertIn("market-scanner-data.js?v=1.1", shell)
        self.assertIn("data/stocks-scanner.json", module)
        self.assertIn("cache: 'no-store'", module)


if __name__ == "__main__":
    unittest.main(verbosity=2)
