from pathlib import Path

HOTFIX = Path('market-hotfix.js')
LEGACY = Path('vestra-ux-v453.js')
OPPS = Path('market-opportunities.js')
FOCUS = Path('vestra-portfolio-focus.js')

h = HOTFIX.read_text(encoding='utf-8')
legacy = LEGACY.read_text(encoding='utf-8')
opps = OPPS.read_text(encoding='utf-8')
focus = FOCUS.read_text(encoding='utf-8')

# Preserve the exact production opportunity contract from v4.53.
critical = (
    "sc==null||sc<58||cov==null||cov<55||conf==null||conf<50",
    "return timing(s)>=48 && confirmed(s)>=2",
    "[n(s?.score),.23]",
    "[timing(s),.27]",
    "[n(s?.recovery_score),.10]",
    "[n(s?.qarp_score),.10]",
    "[n(s?.moat_score),.07]",
    "[n(s?.capital_allocation_intelligence_score),.05]",
    "[n(s?.confidence_score),.06]",
    "[n(s?.value_pct),.06]",
    "[n(s?.growth_pct),.03]",
    "[n(s?.sector_native_score),.03]",
    "Math.min(5,confirmed(s)*1.25)",
)
for token in critical:
    assert token in legacy, f'legacy contract missing: {token}'
    assert token in opps, f'canonical contract changed: {token}'

# Preserve CSS hooks consumed by v454-v456.
for token in ('.ux453-opp', '.ux453-entry'):
    assert token in opps, token
for token in ('.ux453-focusbar', '.ux453-badge', 'vestra-portfolio-focus-v1'):
    assert token in focus, token

old = "  load('./vestra-ux-v453.js?v=4.53','vestraUxV453');\n"
new = (
    "  load('./market-opportunities.js?v=1.0','vestraMarketOpportunities');\n"
    "  load('./vestra-portfolio-focus.js?v=1.0','vestraPortfolioFocus');\n"
)
assert old in h, 'legacy v453 loader marker changed'
h = h.replace(old, new)
h = h.replace('compatibility loader v4.92', 'compatibility loader v4.93')

# v454 political flow was removed; the compatibility hide is now dead code.
style_block = "\n  const style = document.createElement('style');\n  style.id = 'vestra-politicians-canonical-v492';\n  style.textContent = '.politicians-section .ux454-flow{display:none!important}';\n  document.head.appendChild(style);\n"
assert style_block in h, 'legacy political hide marker changed'
h = h.replace(style_block, '\n')

assert 'vestra-ux-v453.js' not in h
assert 'ux454-flow' not in h
assert h.index('market-opportunities.js') < h.index('market-opportunity-lenses.js')
assert h.index('vestra-portfolio-focus.js') < h.index('vestra-ux-v454.js')

HOTFIX.write_text(h, encoding='utf-8')
print('Activated canonical opportunities + portfolio focus; legacy v453 no longer loaded.')
