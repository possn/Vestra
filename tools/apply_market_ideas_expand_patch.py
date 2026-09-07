from pathlib import Path


def replace_once(path, old, new):
    p=Path(path)
    text=p.read_text(encoding='utf-8')
    count=text.count(old)
    if count!=1:
        raise SystemExit(f'{path}: expected 1 match, found {count}: {old[:100]!r}')
    p.write_text(text.replace(old,new,1),encoding='utf-8')

# ETF discovery: use the entire ETF universe, including funds that do not yet
# have a published Vestra score or TER. Theme classification is discovery, not
# score eligibility.
replace_once(
    'market.js',
    "    let funds=M.stocks.filter(isFund).filter(s=>n(s.score)!=null||n(s.expense_ratio)!=null);",
    "    let funds=M.stocks.filter(isFund);"
)
replace_once(
    'market.js',
    "    return `${txt(s.ticker)} ${txt(s.name)} ${txt(s.sector)} ${txt(s.industry)} ${txt(s.category)} ${txt(s.region)}`;",
    "    return `${txt(s.ticker)} ${txt(s.name)} ${txt(s.sector)} ${txt(s.industry)} ${txt(s.category)} ${txt(s.region)} ${txt(s.description)} ${txt(s.long_business_summary)} ${txt(s.business_summary)}`;"
)

# Broaden a few theme vocabularies without touching score/risk semantics.
replacements={
"['technology','Tecnologia',/technology|tech(?:nology)?|digital|software|cloud|internet/i]":"['technology','Tecnologia',/technology|tech(?:nology)?|digital|software|cloud|internet|information technology|computing|saas|platform/i]",
"['semiconductors','Semicondutores',/semiconductor|chip|microchip|semicon|phlx semiconductor/i]":"['semiconductors','Semicondutores',/semiconductor|chip|microchip|semicon|phlx semiconductor|integrated circuit|foundry|wafer|memory chip/i]",
"['ai_robotics','IA & Robótica',/artificial intelligence|(^|[^a-z])ai([^a-z]|$)|robot|automation|robotics/i]":"['ai_robotics','IA & Robótica',/artificial intelligence|machine learning|(^|[^a-z])ai([^a-z]|$)|robot|automation|robotics|autonomous systems/i]",
"['cybersecurity','Cibersegurança',/cyber|security.*tech|digital security/i]":"['cybersecurity','Cibersegurança',/cyber|security.*tech|digital security|network security|information security/i]",
"['water','Água',/water|clean water/i]":"['water','Água',/water|clean water|wastewater|desalination|water infrastructure|water utilities/i]",
"['agriculture','Agricultura',/agricultur|agribusiness|food|fertili[sz]er/i]":"['agriculture','Agricultura',/agricultur|agribusiness|farm|crop|seed|grain|fertili[sz]er|food production/i]",
"['defence','Defesa',/defen[cs]e|aerospace/i]":"['defence','Defesa',/defen[cs]e|aerospace|military|weapons|defense technology/i]",
}
p=Path('market.js'); text=p.read_text(encoding='utf-8')
for old,new in replacements.items():
    if old not in text: raise SystemExit(f'market.js missing theme pattern {old}')
    text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')

# Cache-bust the companion module after the navigation/universe change.
replace_once(
    'market-static-universe.js',
    "script.src = 'market-ui-polish.js?v=1.1&stockthemes=1';",
    "script.src = 'market-ui-polish.js?v=1.1&stockthemes=2';"
)

# Companion v1.1: restore Ideas as native discover mode and provide Ações as a
# separate theme browser. All theme matches are shown, including unscored names.
p=Path('market-stock-themes-tools.js')
text=p.read_text(encoding='utf-8')
text=text.replace('stock theme discovery + tool hierarchy v1.0','stock theme discovery + tool hierarchy v1.1',1)
text=text.replace("  let selectedTheme = '';\n  let observer = null;", "  let selectedTheme = '';\n  let stockBrowserActive = false;\n  let observer = null;",1)
text=text.replace(
"      text: [stock?.ticker, stock?.name, stock?.sector, stock?.industry, stock?.category].map(text).join(' '),",
"      text: [stock?.ticker, stock?.name, stock?.sector, stock?.industry, stock?.category, stock?.description, stock?.long_business_summary, stock?.business_summary].map(text).join(' '),",
1)
text=text.replace(
"  function isStocksMode() {\n    return document.querySelector('[data-market-mode=\"discover\"]')?.classList.contains('is-active') === true;\n  }",
"  function isStocksMode() { return stockBrowserActive; }",
1)
text=text.replace(
"      .map(item => item.stock)\n      .filter(stock => number(stock?.score) != null)\n      .sort((a, b) => (number(b?.score) || 0) - (number(a?.score) || 0));\n    const visible = matches.slice(0, 50);",
"      .map(item => item.stock)\n      .sort((a, b) => {\n        const as=number(a?.score), bs=number(b?.score);\n        if(as==null && bs!=null) return 1;\n        if(bs==null && as!=null) return -1;\n        return (bs||0)-(as||0) || text(a?.name).localeCompare(text(b?.name));\n      });\n    const visible = matches.slice(0, 100);",
1)
text=text.replace(
"        <div><h3>${escapeHtml(theme.label)}</h3><p>Ações classificadas pela atividade/sector disponível, sem alterar o Score ou o Risk Gate.</p></div>",
"        <div><h3>${escapeHtml(theme.label)}</h3><p>Universo temático completo disponível. Empresas sem Score também aparecem; o Score continua separado e não é inventado.</p></div>",
1)

old_rename="""  function renameStocksMode() {
    const label = document.querySelector('[data-market-mode=\"discover\"] strong');
    if (label && label.textContent !== 'Ações') label.textContent = 'Ações';
  }
"""
new_nav="""  function installIdeasAndStocksModes() {
    const ideas = document.querySelector('[data-market-mode=\"discover\"]');
    if (!ideas) return;
    const ideasLabel = ideas.querySelector('strong');
    if (ideasLabel) ideasLabel.textContent = 'Ideias';
    if (document.querySelector('[data-market-stock-browser]')) return;
    const stocksButton = ideas.cloneNode(true);
    stocksButton.removeAttribute('data-market-mode');
    stocksButton.dataset.marketStockBrowser = '1';
    stocksButton.classList.remove('is-active');
    const label = stocksButton.querySelector('strong');
    if (label) label.textContent = 'Ações';
    ideas.insertAdjacentElement('afterend', stocksButton);
  }

  function setModeVisual(activeButton) {
    document.querySelectorAll('[data-market-mode], [data-market-stock-browser]').forEach(button => {
      button.classList.toggle('is-active', button === activeButton);
    });
  }
"""
if old_rename not in text: raise SystemExit('companion renameStocksMode block missing')
text=text.replace(old_rename,new_nav,1)
text=text.replace('    renameStocksMode();','    installIdeasAndStocksModes();',1)

old_click="""    const mode = event.target.closest?.('[data-market-mode]');
    if (mode?.dataset.marketMode === 'discover') {
      selectedTheme = '';
      setTimeout(queueRender, 0);
    }
"""
new_click="""    const stocksMode = event.target.closest?.('[data-market-stock-browser]');
    if (stocksMode) {
      event.preventDefault();
      stockBrowserActive = true;
      selectedTheme = '';
      setModeVisual(stocksMode);
      queueRender();
      return;
    }
    const mode = event.target.closest?.('[data-market-mode]');
    if (mode) {
      stockBrowserActive = false;
      selectedTheme = '';
      setModeVisual(mode);
      if (mode.dataset.marketMode === 'discover') setTimeout(queueRender, 0);
    }
"""
if old_click not in text: raise SystemExit('companion mode click block missing')
text=text.replace(old_click,new_click,1)
text=text.replace("    version: '1.0',","    version: '1.1',",1)
p.write_text(text,encoding='utf-8')

# E2E contract: Ideas remain native; Ações are separate; theme results may be
# unscored and should expose substantially more of the available universe.
p=Path('tests/e2e/market-stock-themes-tools.spec.js')
p.write_text("""const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: Ideias coexist with a separate broad stock-theme browser', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));

  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.evaluate(() => window.setView('market'));
  await page.waitForFunction(() => window.VestraMarketStockThemesTools?.version === '1.1');

  const ideas = page.locator('[data-market-mode="discover"]');
  await expect(ideas.locator('strong')).toHaveText('Ideias');
  await ideas.click();
  await expect(page.locator('.market-discover-section')).toBeVisible({ timeout: 15000 });

  const stocksMode = page.locator('[data-market-stock-browser]');
  await expect(stocksMode.locator('strong')).toHaveText('Ações');
  await stocksMode.click();
  await expect(page.locator('.market-stock-theme-grid')).toBeVisible({ timeout: 15000 });
  await expect(page.locator('#marketPrimary .market-row[data-market-ticker]')).toHaveCount(0);

  const theme = page.locator('[data-market-stock-theme]:not([data-market-stock-theme=""])').first();
  await expect(theme).toBeVisible();
  await theme.click();
  await expect(page.locator('.market-stock-change-theme')).toBeVisible();
  await expect(page.locator('#marketPrimary .market-row[data-market-ticker]').first()).toBeVisible();

  const tools = page.locator('.market-analysis-tools');
  await expect(tools).toBeVisible();
  await expect(tools.locator('[data-market-tool="compare"]')).toBeVisible();
  await expect(tools.locator('[data-market-tool="scanner"]')).toBeVisible();
  expect(errors, `Browser page errors: ${errors.join(' | ')}`).toEqual([]);
});
""",encoding='utf-8')

# Static regression proves ETF discovery no longer gates on score/TER and uses
# descriptive fields for themes.
Path('tests/test_market_theme_universe.py').write_text("""from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
MARKET=(ROOT/'market.js').read_text(encoding='utf-8')
STOCKS=(ROOT/'market-stock-themes-tools.js').read_text(encoding='utf-8')

class MarketThemeUniverseTests(unittest.TestCase):
    def test_etf_theme_discovery_uses_all_known_funds(self):
        self.assertIn('let funds=M.stocks.filter(isFund);', MARKET)
        self.assertNotIn('M.stocks.filter(isFund).filter(s=>n(s.score)!=null||n(s.expense_ratio)!=null)', MARKET)
        self.assertIn('long_business_summary', MARKET)

    def test_ideas_and_stocks_are_separate_surfaces(self):
        self.assertIn("ideasLabel.textContent = 'Ideias'", STOCKS)
        self.assertIn("stocksButton.dataset.marketStockBrowser = '1'", STOCKS)
        self.assertIn("label.textContent = 'Ações'", STOCKS)
        self.assertIn("version: '1.1'", STOCKS)

    def test_stock_theme_results_keep_unscored_companies(self):
        self.assertNotIn('.filter(stock => number(stock?.score) != null)', STOCKS)
        self.assertIn('matches.slice(0, 100)', STOCKS)
        self.assertIn('long_business_summary', STOCKS)

if __name__=='__main__':
    unittest.main(verbosity=2)
""",encoding='utf-8')
