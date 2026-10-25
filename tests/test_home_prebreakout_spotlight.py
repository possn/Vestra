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
        self.assertIn("Melhor sinal da amostra, não do mercado inteiro", SRC)
        self.assertIn("Object.prototype.hasOwnProperty.call(feed, 'daily_focus')", SRC)
        self.assertIn("Sem candidato canónico validado", SRC)
        self.assertIn("Sinal '+pick.date", SRC)
        self.assertIn("Risco: breakout ainda não confirmado", SRC)
        self.assertIn("Score técnico, não probabilidade", SRC)

    def test_preview_uses_real_dossier_data_and_canonical_radar(self):
        self.assertIn("fetchJson", SRC) if "fetchJson" in SRC else self.assertIn("const read=async path", SRC)
        self.assertIn("data/dossiers-manifest.json", SRC)
        self.assertIn("data/dossiers/", SRC)
        self.assertIn("price_history_1y", SRC)
        self.assertIn("VestraDossierRadarAxes?.(stock)", SRC)
        self.assertIn("await appendMiniDossier(pick)", SRC)
        self.assertIn("Histórico de preço insuficiente", SRC)
        self.assertIn("não prevê breakout", SRC)
        self.assertNotIn("preview.innerHTML", SRC)

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
