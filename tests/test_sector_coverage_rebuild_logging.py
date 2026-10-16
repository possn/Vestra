import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class SectorCoverageRebuildContract(unittest.TestCase):
    def test_canonical_rebuild_emits_auditable_sector_coverage(self):
        code = (ROOT / "scripts" / "run.py").read_text(encoding="utf-8")
        self.assertIn("from audit_sector_relative_coverage import report as sector_coverage_report", code)
        self.assertIn("coverage = sector_coverage_report(payload)", code)
        self.assertIn('log.info("SECTOR_RELATIVE_COVERAGE %s"', code)
        self.assertLess(code.index("sector_coverage_report(payload)"),
                        code.index('log.info("SECTOR_RELATIVE_COVERAGE %s"'))
if __name__ == "__main__":
    unittest.main()
