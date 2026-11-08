"""Run the real politicians.js identity regression as part of historical CI."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PoliticiansIdentityTests(unittest.TestCase):
    def test_two_members_with_same_name_do_not_share_trades(self):
        result = subprocess.run(
            ["node", str(ROOT / "tests/runtime_politicians_member_identity_contract.js")],
            cwd=ROOT, capture_output=True, text=True, timeout=15, check=False
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("politician member identity regression: ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
