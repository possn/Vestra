import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MarketOpportunityOverlapAuditTests(unittest.TestCase):
    def test_exact_runtime_lenses_emit_quantitative_overlap_report(self):
        proc = subprocess.run(
            ['node', 'scripts/audit_opportunity_overlap.js', '12'],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        report = json.loads(proc.stdout)
        self.assertGreater(report['universe_count'], 0)
        self.assertEqual(report['top_n'], 12)
        self.assertEqual(set(report['ranked']), {'all', 'low52', 'emerging', 'recovery', 'value'})
        for lens, tickers in report['ranked'].items():
            self.assertLessEqual(len(tickers), 12, lens)
            self.assertEqual(len(tickers), len(set(tickers)), lens)
        print('OPPORTUNITY_OVERLAP_AUDIT=' + json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    unittest.main(verbosity=2)
