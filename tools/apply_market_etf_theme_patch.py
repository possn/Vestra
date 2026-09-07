from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, found {count} for {old[:100]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Dossier controls: preserve unified geometry, move the pair closer to the right edge.
p = Path("market-dossier-controls.js")
text = p.read_text(encoding="utf-8")
text = text.replace("Market Dossier Controls v1.2", "Market Dossier Controls v1.3", 1)
text = text.replace(
    "right:max(calc(env(safe-area-inset-right) + 14px),14px) !important;",
    "right:max(calc(env(safe-area-inset-right) + 3px),3px) !important;",
    1,
)
text = text.replace("version: '1.2'", "version: '1.3'", 1)
p.write_text(text, encoding="utf-8")

# Explicit ETF theme state.
replace_once(
    "market.js",
    "    sector: 'all',\n    region: 'all',",
    "    sector: 'all',\n    region: 'all',\n    fundTheme: '',",
)

old_render = '''  function renderFunds(){
    const qs=M.query.toLowerCase();
    let funds=M.stocks.filter(isFund);
    if(qs) funds=funds.filter(s=>`${s.ticker} ${s.name} ${s.region||''} ${s.sector||''}`.toLowerCase().includes(qs));
    funds=funds.filter(s=>n(s.score)!=null||n(s.expense_ratio)!=null).sort((a,b)=>(n(b.score)||0)-(n(a.score)||0)).slice(0,24);
    return `<section class="market-section"><div class="market-section__head"><div><h3>ETFs</h3><p>Catálogo independente da tua carteira. Abre um fundo para ver custo, score e encaixe.</p></div><span class="market-data-age">${ageText()}</span></div><div class="market-list">${funds.length?funds.map(s=>renderRow(s,[n(s.expense_ratio)!=null?`TER ${pct(s.expense_ratio)}`:'',txt(s.region)].filter(Boolean).join(' · '))).join(''):'<div class="market-empty">Sem ETFs encontrados.</div>'}</div></section>`;
  }
'''

new_render = '''  const ETF_THEMES=[
    ['technology','Tecnologia',/technology|tech(?:nology)?|digital|software|cloud|internet/i],
    ['semiconductors','Semicondutores',/semiconductor|chip|microchip|semicon|phlx semiconductor/i],
    ['ai_robotics','IA & Robótica',/artificial intelligence|(^|[^a-z])ai([^a-z]|$)|robot|automation|robotics/i],
    ['cybersecurity','Cibersegurança',/cyber|security.*tech|digital security/i],
    ['healthcare','Saúde',/health|healthcare|medical|pharma|pharmaceutical/i],
    ['biotech','Biotecnologia',/biotech|biotechnology|genomic|genomics/i],
    ['energy','Energia',/energy|oil|gas|petroleum|exploration|natural gas/i],
    ['clean_energy','Energia limpa',/clean energy|renewable|solar|wind|hydrogen|decarbon/i],
    ['nuclear_uranium','Nuclear & Urânio',/uranium|nuclear/i],
    ['gold','Ouro',/gold|gold miner|gold mining/i],
    ['silver_metals','Prata & Metais',/silver|precious metal|metals|mining|copper|lithium/i],
    ['water','Água',/water|clean water/i],
    ['agriculture','Agricultura',/agricultur|agribusiness|food|fertili[sz]er/i],
    ['defence','Defesa',/defen[cs]e|aerospace/i],
    ['infrastructure','Infraestruturas',/infrastructure/i],
    ['real_estate','Imobiliário',/real estate|reit|property/i],
    ['dividend','Dividendos',/dividend|income|high yield equity/i],
    ['bonds','Obrigações',/bond|treasury|fixed income|corporate debt|government debt/i],
    ['emerging','Emergentes',/emerging market|emerging markets/i],
    ['china','China',/china|chinese|csi 300|hang seng/i],
    ['europe','Europa',/europe|eurozone|stoxx|european/i],
    ['world','Mundial',/world|global|all-world|all world|msci acwi/i],
    ['sp500','S&P 500',/s&p\\s*500|sp 500|s&p500/i],
    ['nasdaq','Nasdaq',/nasdaq|qqq/i],
    ['small_caps','Small Caps',/small cap|small-cap|smallcap/i],
  ];

  function fundThemeText(s){
    return `${txt(s.ticker)} ${txt(s.name)} ${txt(s.sector)} ${txt(s.industry)} ${txt(s.category)} ${txt(s.region)}`;
  }

  function fundMatchesTheme(s,key){
    const def=ETF_THEMES.find(x=>x[0]===key);
    return Boolean(def && def[2].test(fundThemeText(s)));
  }

  function renderFunds(){
    const qs=M.query.toLowerCase();
    let funds=M.stocks.filter(isFund).filter(s=>n(s.score)!=null||n(s.expense_ratio)!=null);
    const available=ETF_THEMES.map(([key,label,matcher])=>({
      key,label,count:funds.filter(s=>matcher.test(fundThemeText(s))).length
    })).filter(x=>x.count>0);

    if(qs){
      funds=funds.filter(s=>fundThemeText(s).toLowerCase().includes(qs));
      funds.sort((a,b)=>(n(b.score)||0)-(n(a.score)||0));
      return `<section class="market-section"><div class="market-section__head"><div><h3>ETFs · pesquisa</h3><p>Resultados para ${esc(M.query)}.</p></div><span class="market-data-age">${funds.length}</span></div><div class="market-list">${funds.length?funds.map(s=>renderRow(s,[n(s.expense_ratio)!=null?`TER ${pct(s.expense_ratio)}`:'',txt(s.region)].filter(Boolean).join(' · '))).join(''):'<div class="market-empty">Sem ETFs encontrados.</div>'}</div></section>`;
    }

    if(!M.fundTheme){
      return `<section class="market-section market-etf-discovery"><div class="market-section__head"><div><h3>Escolher ETFs por tema</h3><p>Escolhe primeiro a exposição que procuras. Só depois mostramos os fundos desse tema.</p></div><span class="market-data-age">${funds.length} fundos</span></div><div class="market-etf-theme-grid" role="group" aria-label="Temas de ETF">${available.map(x=>`<button type="button" class="market-etf-theme" data-market-fund-theme="${esc(x.key)}"><strong>${esc(x.label)}</strong><span>${x.count} ${x.count===1?'ETF':'ETFs'}</span></button>`).join('')}</div></section>`;
    }

    const theme=available.find(x=>x.key===M.fundTheme);
    funds=funds.filter(s=>fundMatchesTheme(s,M.fundTheme)).sort((a,b)=>(n(b.score)||0)-(n(a.score)||0));
    return `<section class="market-section market-etf-discovery"><div class="market-section__head"><div><h3>${esc(theme?.label||'ETFs')}</h3><p>ETFs classificados pela exposição temática disponível.</p></div><button type="button" class="market-etf-change-theme" data-market-fund-theme="">Mudar tema</button></div><div class="market-list">${funds.length?funds.map(s=>renderRow(s,[n(s.expense_ratio)!=null?`TER ${pct(s.expense_ratio)}`:'',txt(s.region)].filter(Boolean).join(' · '))).join(''):'<div class="market-empty">Sem ETFs encontrados neste tema.</div>'}</div></section>`;
  }
'''
replace_once("market.js", old_render, new_render)

replace_once(
    "market.js",
    "    const mode=e.target.closest('[data-market-mode]'); if(mode){M.mode=mode.dataset.marketMode; document.querySelectorAll('[data-market-mode]').forEach(x=>x.classList.toggle('is-active',x===mode)); renderPrimary(); if(M.mode==='smart') loadCongressLive().then(()=>renderPrimary());}",
    "    const mode=e.target.closest('[data-market-mode]'); if(mode){const nextMode=mode.dataset.marketMode; if(nextMode==='funds'&&M.mode!=='funds') M.fundTheme=''; M.mode=nextMode; document.querySelectorAll('[data-market-mode]').forEach(x=>x.classList.toggle('is-active',x===mode)); renderPrimary(); if(M.mode==='smart') loadCongressLive().then(()=>renderPrimary());}",
)
replace_once(
    "market.js",
    "    const sec=e.target.closest('[data-market-sector]'); if(sec){M.sector=sec.dataset.marketSector;renderPrimary();}\n    const watch=e.target.closest('[data-market-watch]');",
    "    const sec=e.target.closest('[data-market-sector]'); if(sec){M.sector=sec.dataset.marketSector;renderPrimary();}\n    const fundTheme=e.target.closest('[data-market-fund-theme]'); if(fundTheme){M.fundTheme=fundTheme.dataset.marketFundTheme||'';renderPrimary();return;}\n    const watch=e.target.closest('[data-market-watch]');",
)

css = Path("market.css")
css_text = css.read_text(encoding="utf-8")
css_text += '''

/* v2.7 — ETF discovery by theme */
.market-etf-theme-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:4px}
.market-etf-theme{min-width:0;border:1px solid var(--line);background:var(--card2);color:var(--text);border-radius:16px;padding:12px;text-align:left;cursor:pointer;box-shadow:none}
.market-etf-theme strong{display:block;font-size:12px;line-height:1.25}
.market-etf-theme span{display:block;margin-top:4px;color:var(--muted);font-size:10px;font-weight:700}
.market-etf-theme:active{transform:scale(.985)}
.market-etf-change-theme{flex:0 0 auto;border:1px solid var(--line);background:var(--card2);color:var(--text2);border-radius:999px;padding:7px 10px;font:inherit;font-size:10px;font-weight:800;cursor:pointer}
@media(min-width:640px){.market-etf-theme-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
'''
css.write_text(css_text, encoding="utf-8")

Path("tests/e2e/market-etf-themes.spec.js").write_text('''const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: ETFs start with themes and reveal funds only after choosing one', async ({ page }) => {
  const errors=[];
  page.on('pageerror', e=>errors.push(e.message));
  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.evaluate(() => window.setView('market'));
  const etfMode=page.locator('[data-market-mode="funds"]');
  await expect(etfMode).toBeVisible();
  await etfMode.click();
  await expect(page.locator('.market-etf-theme-grid')).toBeVisible({timeout:15000});
  await expect(page.locator('#marketPrimary .market-row[data-market-ticker]')).toHaveCount(0);
  const theme=page.locator('[data-market-fund-theme]:not([data-market-fund-theme=""])').first();
  await expect(theme).toBeVisible();
  await theme.click();
  await expect(page.locator('.market-etf-change-theme')).toBeVisible();
  await expect(page.locator('#marketPrimary .market-row[data-market-ticker]').first()).toBeVisible();
  expect(errors, `Browser page errors: ${errors.join(' | ')}`).toEqual([]);
});
''', encoding="utf-8")

dp = Path("tests/e2e/market-dossier-controls.spec.js")
dt = dp.read_text(encoding="utf-8")
needle = "  expect(geometry.flexShrink).toBe('0');\n\n  await close.click();"
replacement = "  expect(geometry.flexShrink).toBe('0');\n  const closeEdge = await close.evaluate(el => ({ right: el.getBoundingClientRect().right, viewport: window.innerWidth }));\n  expect(closeEdge.viewport - closeEdge.right).toBeLessThanOrEqual(8);\n\n  await close.click();"
if needle not in dt:
    raise SystemExit("tests/e2e/market-dossier-controls.spec.js: geometry insertion point missing")
dp.write_text(dt.replace(needle, replacement, 1), encoding="utf-8")
