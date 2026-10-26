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

    def test_compact_visuals_use_actual_dossier_evidence(self):
        self.assertIn("window.VestraMarketData?.hydrateTicker", SRC)
        self.assertIn("fetch('./data/dossiers-manifest.json'", SRC)
        self.assertIn("fetch('./data/dossiers/'+bucket+'.json'", SRC)
        self.assertIn("stock?.ticker!==pick.ticker", SRC)
        self.assertIn("stock.price_history_1y", SRC)
        self.assertIn("close.length >= 2", SRC)
        self.assertIn("stock.value_pct", SRC)
        self.assertIn("stock.dividend_fcf_coverage", SRC)
        self.assertIn("PERFIL FUNDAMENTAL · 5 EIXOS", SRC)
        self.assertIn("Histórico por confirmar", SRC)
        self.assertIn("Fundamentais por confirmar", SRC)
        self.assertIn("void showPrebreakoutVisuals(panel, pick)", SRC)

    def test_compression_watch_keeps_real_visuals_without_qualification(self):
        self.assertIn("source+' · Vigilância, não recomendação.',true,watch,false);", SRC)
        self.assertIn("void showPrebreakoutVisuals(panel, watch);", SRC)
        self.assertIn("void showPrebreakoutVisuals(panel, pick);", SRC)
        self.assertIn("if(active && pick?.ticker)", SRC)

    def test_watch_visual_assets_have_current_cache_generation(self):
        html=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")
        self.assertIn("vestra-intelligence-home.js?v=34&amp;rev=20261025-income-privacy",html)
        self.assertIn("vestra-prebreakout-home.css?v=2-watch-visuals",html)
        self.assertIn("void showPrebreakoutVisuals(panel, watch);",SRC)

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
