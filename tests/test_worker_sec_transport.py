from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WorkerSecTransportTests(unittest.TestCase):
    def test_runtime_contract(self):
        proc = subprocess.run(
            ["node", "--experimental-default-type=module", "tests/runtime_worker_sec_transport_contract.mjs"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            self.fail(proc.stdout + "\n" + proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
