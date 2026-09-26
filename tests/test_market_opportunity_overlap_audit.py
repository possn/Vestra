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
        self.assertEqual(len(report['ranked']['all']), 12)
        self.assertLessEqual(
            report['pairs']['all__recovery']['overlap_of_top_n_pct'],
            50.0,
            'general shortlist must not be dominated by the recovery lens',
        )
        diag = report['general_shortlist_diagnostics']
        self.assertLessEqual(diag['max_sector_share_pct'], 25.0)
        self.assertLessEqual(diag['max_industry_share_pct'], 16.7)
        self.assertGreaterEqual(diag['distinct_sectors'], 4)
        self.assertGreaterEqual(diag['distinct_industries'], 6)
        self.assertGreaterEqual(diag['distinct_dominant_sleeves'], 2)
        represented = sum(1 for count in diag['archetype_counts'].values() if count > 0)
        self.assertGreaterEqual(represented, 3)
        print('OPPORTUNITY_OVERLAP_AUDIT=' + json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    unittest.main(verbosity=2)
