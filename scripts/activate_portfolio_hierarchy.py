from pathlib import Path

HOTFIX=Path('market-hotfix.js')
V454=Path('vestra-ux-v454.js')
CANON=Path('vestra-portfolio-hierarchy.js')

h=HOTFIX.read_text(encoding='utf-8')
v=V454.read_text(encoding='utf-8')
c=CANON.read_text(encoding='utf-8')

for token in (
    "kinds:['research','priority','reinforce','review']",
    "kinds:['swap','scenario','overlap','map']",
    "kinds:['target','history','risk','stress']",
    'ux454-swap-head','ux454-overlap-head','ux455-swap-summary','ux455-overlap-note',
    'new MutationObserver',
):
    assert token in c, token

# v454 keeps only opportunity podium/presentation; canonical hierarchy owns portfolio DOM.
start=v.index('  const GROUPS=[')
end=v.index('  function rankOpportunityRows(){', start)
v=v[:start]+v[end:]
v=v.replace('  function apply(){organizePortfolio();rankOpportunityRows();}\n','  function apply(){rankOpportunityRows();}\n')
for token in ('organizePortfolio','makeGroupLabel','GROUPS','ux454-nav-title'):
    assert token not in v, token
assert 'rankOpportunityRows' in v
assert 'ux454-podium' in v

old=(
    "  load('./vestra-ux-v454.js?v=4.54','vestraUxV454');\n"
    "  load('./vestra-ux-v455.js?v=4.55','vestraUxV455');\n"
    "  load('./vestra-ux-v456.js?v=4.56','vestraUxV456');\n"
    "  load('./vestra-ux-v457.js?v=4.57','vestraUxV457');\n"
)
new=(
    "  load('./vestra-ux-v454.js?v=4.54','vestraUxV454');\n"
    "  load('./vestra-portfolio-hierarchy.js?v=1.0','vestraPortfolioHierarchy');\n"
    "  load('./vestra-ux-v456.js?v=4.56','vestraUxV456');\n"
)
assert old in h, 'v454-v457 loader sequence changed'
h=h.replace(old,new)
h=h.replace('compatibility loader v4.94','compatibility loader v4.95')
assert 'vestra-ux-v455.js' not in h
assert 'vestra-ux-v457.js' not in h
assert h.index('vestra-portfolio-hierarchy.js') < h.index('vestra-ux-v456.js')

HOTFIX.write_text(h,encoding='utf-8')
V454.write_text(v,encoding='utf-8')
print('Activated canonical portfolio hierarchy; v454 now opportunity presentation only.')
