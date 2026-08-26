from pathlib import Path


def strip_block(text: str, start_marker: str, end_marker: str) -> str:
    if text.count(start_marker) != 1:
        raise SystemExit(f'unexpected marker count: {start_marker}')
    start = text.find(start_marker)
    end = text.find(end_marker, start)
    if start < 0 or end < 0 or end <= start:
        raise SystemExit(f'block markers not found: {start_marker} -> {end_marker}')
    return text[:start] + text[end:]

# v453: remove legacy politician summary only.
p453 = Path('vestra-ux-v453.js')
t453 = p453.read_text(encoding='utf-8')
t453 = strip_block(t453, '  function politicianSummary(){', '  function style(){')
lines = [line for line in t453.splitlines() if '.ux453-politician-summary' not in line]
t453 = '\n'.join(lines) + '\n'
old = '  function apply(){opportunities();portfolioFocus();politicianSummary();}'
new = '  function apply(){opportunities();portfolioFocus();}'
if old not in t453:
    raise SystemExit('v453 apply block not found')
t453 = t453.replace(old, new, 1)
for token in ('politicianSummary', 'ux453-politician-summary', '.politicians-section'):
    if token in t453:
        raise SystemExit(f'v453 political token remains: {token}')
for token in ('opportunities()', 'portfolioFocus()', 'ux453-focusbar'):
    if token not in t453:
        raise SystemExit(f'v453 required behavior missing: {token}')
p453.write_text(t453, encoding='utf-8')

# v454: remove direct Bargo fetch and duplicate political-flow UI.
p454 = Path('vestra-ux-v454.js')
t454 = p454.read_text(encoding='utf-8')
if 'let recentPolitical=null;' not in t454:
    raise SystemExit('v454 political state marker missing')
t454 = t454.replace('  let recentPolitical=null;\n\n', '', 1)
t454 = strip_block(t454, '  async function loadPoliticalFlow(){', '  function style(){')
lines = [line for line in t454.splitlines() if '.ux454-flow' not in line]
t454 = '\n'.join(lines) + '\n'
old = '  function apply(){organizePortfolio();rankOpportunityRows();enhancePoliticalFlow();}'
new = '  function apply(){organizePortfolio();rankOpportunityRows();}'
if old not in t454:
    raise SystemExit('v454 apply block not found')
t454 = t454.replace(old, new, 1)
for token in ('recentPolitical', 'loadPoliticalFlow', 'enhancePoliticalFlow', 'www.bargo.ai', 'ux454-flow', '.politicians-section'):
    if token in t454:
        raise SystemExit(f'v454 political token remains: {token}')
for token in ('organizePortfolio()', 'rankOpportunityRows()', 'ux454-opportunity-guide'):
    if token not in t454:
        raise SystemExit(f'v454 required behavior missing: {token}')
p454.write_text(t454, encoding='utf-8')

print('Removed duplicate political overlays from v453 and v454; retained portfolio/opportunity behavior.')
