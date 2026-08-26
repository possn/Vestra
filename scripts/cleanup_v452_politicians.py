from pathlib import Path

PATH = Path('vestra-ux-v452.js')
text = PATH.read_text(encoding='utf-8')

start = text.find('  function enhancePoliticians(){')
end = text.find('  function addStyle(){', start)
if start < 0 or end < 0 or end <= start:
    raise SystemExit('politician enhancement block markers not found exactly')
if text.count('  function enhancePoliticians(){') != 1:
    raise SystemExit('unexpected enhancePoliticians marker count')

text = text[:start] + text[end:]

politician_css_tokens = (
    '.ux-politician-search',
    '.ux-politician-matches',
    '.ux-politician-controls',
    '.ux-politician-pulse',
)
lines = []
for line in text.splitlines():
    if any(token in line for token in politician_css_tokens):
        continue
    lines.append(line)
text = '\n'.join(lines) + '\n'

old_apply = "  function apply(){refineOpportunities();classifyPortfolioCards();enhancePoliticians();const p=document.querySelector('.politicians-section');if(p){applyPoliticianView(p);addPoliticianPulse(p);}}"
new_apply = "  function apply(){refineOpportunities();classifyPortfolioCards();}"
if old_apply not in text:
    raise SystemExit('canonical apply block not found')
text = text.replace(old_apply, new_apply, 1)

for forbidden in (
    'enhancePoliticians',
    'applyPoliticianView',
    'addPoliticianPulse',
    'vestra-politician-favourites-v1',
    'data-ux-politician-view',
    'data-ux-politician-fav',
    'ux-politician-search',
    'ux-politician-controls',
    'ux-politician-pulse',
):
    if forbidden in text:
        raise SystemExit(f'legacy politician token remains: {forbidden}')

for required in ('refineOpportunities()', 'classifyPortfolioCards()', 'function addStyle(){', 'function jumpPortfolio(kind)'):
    if required not in text:
        raise SystemExit(f'non-politician v452 behavior missing: {required}')

PATH.write_text(text, encoding='utf-8')
print('Removed legacy politician UI from v452; retained opportunity and portfolio behavior.')
