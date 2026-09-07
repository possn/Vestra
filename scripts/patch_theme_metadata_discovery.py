from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(path, old, new):
    p = ROOT / path
    text = p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'expected block not found in {path}: {old[:120]!r}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')


replace(
    'market-stock-themes-tools.js',
    '/* Vestra Market stock theme discovery + tool hierarchy v1.1 */',
    '/* Vestra Market stock theme discovery + tool hierarchy v1.2 */',
)
replace(
    'market-stock-themes-tools.js',
    "text: [stock?.ticker, stock?.name, stock?.sector, stock?.industry, stock?.category, stock?.description, stock?.long_business_summary, stock?.business_summary].map(text).join(' '),",
    "text: [stock?.ticker, stock?.name, stock?.sector, stock?.industry, stock?.category, stock?.theme, stock?.style, stock?.description, stock?.long_business_summary, stock?.business_summary].map(text).join(' '),",
)
replace(
    'market-stock-themes-tools.js',
    "version: '1.1',",
    "version: '1.2',",
)
replace(
    'market.js',
    'return `${txt(s.ticker)} ${txt(s.name)} ${txt(s.sector)} ${txt(s.industry)} ${txt(s.category)} ${txt(s.region)} ${txt(s.description)} ${txt(s.long_business_summary)} ${txt(s.business_summary)}`;',
    'return `${txt(s.ticker)} ${txt(s.name)} ${txt(s.sector)} ${txt(s.industry)} ${txt(s.category)} ${txt(s.region)} ${txt(s.theme)} ${txt(s.style)} ${txt(s.ucits)} ${txt(s.description)} ${txt(s.long_business_summary)} ${txt(s.business_summary)}`;',
)
replace(
    'tests/e2e/market-stock-themes-tools.spec.js',
    "window.VestraMarketStockThemesTools?.version === '1.1'",
    "window.VestraMarketStockThemesTools?.version === '1.2'",
)
replace(
    'tests/test_market_theme_universe.py',
    "        self.assertIn('long_business_summary', MARKET)\n",
    "        self.assertIn('long_business_summary', MARKET)\n        self.assertIn('${txt(s.theme)} ${txt(s.style)} ${txt(s.ucits)}', MARKET)\n",
)
replace(
    'tests/test_market_theme_universe.py',
    "        self.assertIn(\"version: '1.1'\", STOCKS)\n",
    "        self.assertIn(\"version: '1.2'\", STOCKS)\n        self.assertIn('stock?.theme, stock?.style', STOCKS)\n",
)

print('Theme metadata discovery patch applied.')
