from pathlib import Path
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]


class PoliticiansAtomicFeedTests(unittest.TestCase):
    def test_feed_commits_together_after_executive_download(self):
        run=subprocess.run(["node",str(ROOT/"tests/runtime_politicians_atomic_snapshot.js")],
                           cwd=ROOT,capture_output=True,text=True,timeout=15,check=False)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        self.assertIn("politician atomic feed regression: ok",run.stdout)


if __name__=="__main__":
    unittest.main()
