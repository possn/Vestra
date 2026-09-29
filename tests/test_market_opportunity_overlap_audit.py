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
        self.assertGreater(len(report['ranked']['all']), 0)
        self.assertLessEqual(len(report['ranked']['all']), 12)
        self.assertLessEqual(
            report['pairs']['all__recovery']['overlap_of_top_n_pct'],
            50.0,
            'general shortlist must not be dominated by the recovery lens',
        )
        eligibility = report['general_shortlist_eligibility']
        self.assertEqual(eligibility['eligible_count'], len(report['ranked']['all']))
        self.assertEqual(eligibility['ineligible_count'], 0)
        self.assertEqual(eligibility['ineligible'], [])
        self.assertEqual(eligibility['published_contract_violation_count'], 0)
        self.assertEqual(eligibility['published_contract_violations'], [])
        funnel = report['opportunity_funnel']
        self.assertEqual(funnel['universe_count'], report['universe_count'])
        self.assertLessEqual(funnel['published_eligible_score_54plus_count'], funnel['published_eligible_count'])
        self.assertLessEqual(funnel['strong_tier_count'], funnel['published_eligible_score_54plus_count'])
        for key in (
            'labels', 'upside_support', 'risk_gate', 'event_risk',
            'market_regime', 'revision_evidence', 'valuation_evidence',
            'suppressed_reasons', 'cap_reasons', 'actionable_labels',
            'actionable_support', 'actionable_risk_gate', 'actionable_sectors',
            'actionable_unknown_sector_tickers', 'actionable_unknown_industry_tickers',
        ):
            self.assertIn(key, funnel)
        self.assertEqual(sum(funnel['labels'].values()), report['universe_count'])
        self.assertEqual(sum(funnel['upside_support'].values()), report['universe_count'])
        self.assertEqual(sum(funnel['risk_gate'].values()), report['universe_count'])
        self.assertEqual(
            len(funnel['actionable_unknown_sector_tickers']),
            funnel['actionable_sectors'].get('Unknown', 0),
        )
        diag = report['general_shortlist_diagnostics']
        self.assertLessEqual(max(diag['sector_counts'].values(), default=0), 3)
        self.assertLessEqual(max(diag['industry_counts'].values(), default=0), 2)
        self.assertIn('unknown_sector_tickers', diag)
        self.assertIn('unknown_industry_tickers', diag)
        self.assertEqual(len(diag['unknown_sector_tickers']), diag['sector_counts'].get('Unknown', 0))
        self.assertEqual(len(diag['unknown_industry_tickers']), diag['industry_counts'].get('Unknown', 0))
        self.assertGreaterEqual(diag['distinct_sectors'], min(3, len(report['ranked']['all'])))
        self.assertGreaterEqual(diag['distinct_industries'], min(3, len(report['ranked']['all'])))
        self.assertGreaterEqual(diag['distinct_dominant_sleeves'], 1)
        for sleeve in ('strength', 'asymmetry', 'inflection'):
            summary = diag['sleeve_score_summary'][sleeve]
            self.assertIsNotNone(summary['median'])
            self.assertGreaterEqual(summary['min'], 0)
            self.assertLessEqual(summary['max'], 100)
        represented = sum(1 for count in diag['archetype_counts'].values() if count > 0)
        self.assertGreaterEqual(represented, 1)
        novelty = report['discovery_novelty_vs_score']
        self.assertEqual(len(novelty['top_score_ranked']), 12)
        self.assertEqual(
            novelty['discovery_novel_count'] + novelty['discovery_in_top_score_decile_count'],
            len(report['ranked']['all']),
        )
        print('OPPORTUNITY_OVERLAP_AUDIT=' + json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    unittest.main(verbosity=2)
