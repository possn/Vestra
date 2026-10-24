from pathlib import Path
import unittest

SRC=(Path(__file__).resolve().parents[1]/'vestra-intelligence-home.js').read_text(encoding='utf-8')

class PrebreakoutDailyHomeContract(unittest.TestCase):
    def test_first_look_is_real_feed_and_no_synthetic_pick(self):
        self.assertIn("fetch('./data/prebreakout-signals.json'", SRC)
        self.assertIn("feed?.schema === 'vestra_prebreakout_v1'", SRC)
        self.assertIn("hours >= 0 && hours <= 72", SRC)
        self.assertIn("row.stage === 'pré-breakout' && row.volumeDry === true", SRC)
        self.assertIn("row.breakoutExtensionPct <= 0", SRC)
        self.assertIn("Sem pré-breakout qualificado hoje", SRC)
        self.assertIn("Radar indisponível ou desatualizado", SRC)
        self.assertIn("Melhor sinal da amostra analisada, não de todo o mercado.", SRC)
        self.assertIn("Score técnico, não probabilidade", SRC)

    def test_navigation_and_safe_text(self):
        self.assertIn("action.dataset.vestraGo='market'", SRC)
        self.assertIn("action.dataset.vestraTicker=pick.ticker", SRC)
        self.assertIn("if(active && pick?.ticker)", SRC)
        self.assertIn("VestraNavigation?.openCompany?.(ticker,{origin:'market',sourceNode:button})", SRC)
        self.assertIn("await market.ensureLoaded()", SRC)
        self.assertIn("document.getElementById('marketSheet')?.dataset.ticker === ticker", SRC)
        self.assertIn("element('h3','vi-pb-heading',title)", SRC)
        self.assertIn("element('p','vi-pb-detail',detail)", SRC)
        self.assertIn("showPrebreakoutSpotlight(host);", SRC)
        self.assertNotIn("panel.innerHTML =", SRC)

if __name__ == '__main__':
    unittest.main()
