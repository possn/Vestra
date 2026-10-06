from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ZombieRiskIntegrationContract(unittest.TestCase):
    def test_engine_is_independent_from_score_and_published_to_portfolio_index(self):
        run = (ROOT / 'scripts' / 'run.py').read_text(encoding='utf-8')
        score = (ROOT / 'scripts' / 'score.py').read_text(encoding='utf-8')
        shards = (ROOT / 'scripts' / 'build_market_shards.py').read_text(encoding='utf-8')
        portfolio = (ROOT / 'portfolio-diagnostics.js').read_text(encoding='utf-8')
        self.assertIn('raw = enrich_zombie_risk(raw)', run)
        self.assertIn('row["zombie_risk_status"]', run)
        self.assertNotIn('zombie_risk_status', score)
        self.assertIn('"zombie_risk_status"', shards)
        self.assertIn('data-ux-kind="zombie"', portfolio)
        self.assertIn('não altera automaticamente o Vestra Score', portfolio)


if __name__ == '__main__':
    unittest.main()
