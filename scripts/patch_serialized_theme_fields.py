from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def replace(path, old, new):
    p = ROOT / path
    text = p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'expected block not found in {path}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')

replace(
    'market-stock-themes-tools.js',
    "stock?.category, stock?.theme, stock?.style, stock?.description",
    "stock?.category, stock?.theme, stock?.stock_theme, stock?.style, stock?.description",
)
replace(
    'market-stock-themes-tools.js',
    "/* Vestra Market stock theme discovery + tool hierarchy v1.2 */",
    "/* Vestra Market stock theme discovery + tool hierarchy v1.3 */",
)
replace(
    'market-stock-themes-tools.js',
    "version: '1.2',",
    "version: '1.3',",
)
replace(
    'market.js',
    '${txt(s.theme)} ${txt(s.style)} ${txt(s.ucits)}',
    '${txt(s.theme)} ${txt(s.fund_theme)} ${txt(s.style)} ${txt(s.fund_style)} ${txt(s.ucits)} ${txt(s.fund_ucits)}',
)
replace(
    'tests/e2e/market-stock-themes-tools.spec.js',
    "window.VestraMarketStockThemesTools?.version === '1.2'",
    "window.VestraMarketStockThemesTools?.version === '1.3'",
)
replace(
    'tests/test_market_theme_universe.py',
    "${txt(s.theme)} ${txt(s.style)} ${txt(s.ucits)}",
    "${txt(s.theme)} ${txt(s.fund_theme)} ${txt(s.style)} ${txt(s.fund_style)} ${txt(s.ucits)} ${txt(s.fund_ucits)}",
)
replace(
    'tests/test_market_theme_universe.py',
    "version: '1.2'",
    "version: '1.3'",
)
replace(
    'tests/test_market_theme_universe.py',
    "stock?.theme, stock?.style",
    "stock?.theme, stock?.stock_theme, stock?.style",
)

print('Serialized theme field patch applied.')
