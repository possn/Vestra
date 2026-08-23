from pathlib import Path
import re

root=Path(__file__).resolve().parents[1]

# --- app.js: repair quote identity scope without weakening quote safety ---
p=root/'app.js'
s=p.read_text()
marker='function quoteSanityCheck(asset, q, priceEur, rawTicker) {'
assert marker in s
if 'function hasStrongQuoteIdentitySafe(asset)' not in s:
    helper=r'''function hasStrongQuoteIdentitySafe(asset) {
  if (!asset) return false;
  const cls = normalizeTickerLookupKey(asset.class || "");
  if (cls === "CRIPTO" || cls === "CRYPTO") return true;
  const isin = String(asset.isin || "").trim().toUpperCase();
  if (/^[A-Z]{2}[A-Z0-9]{9}\d$/.test(isin)) return true;
  if (typeof hasExplicitTickerTag === "function" && hasExplicitTickerTag(asset)) return true;
  const storedYahoo = String(asset.yahooTicker || "").trim().toUpperCase();
  if (storedYahoo && typeof isPlausibleMarketTicker === "function" && isPlausibleMarketTicker(storedYahoo, asset)) return true;
  const raw = String(asset.ticker || asset.symbol || "").trim().toUpperCase();
  if (raw && typeof isPlausibleMarketTicker === "function" && isPlausibleMarketTicker(raw, asset)) return true;
  return false;
}

'''
    s=s.replace(marker,helper+marker,1)
s=s.replace('const explicit = hasStrongQuoteIdentity(asset);','const explicit = hasStrongQuoteIdentitySafe(asset);')
# Any eligibility calls outside the accidentally nested helper must also have a visible helper.
s=s.replace('if (asset.generatedFromBroker && !hasStrongQuoteIdentity(asset)) return false;','if (asset.generatedFromBroker && !hasStrongQuoteIdentitySafe(asset)) return false;')
s=s.replace('return !!(isin || (hasStrongQuoteIdentity(asset) && (raw || storedYahoo || inferredYahoo || isPlausibleMarketTicker(raw, asset))));','return !!(isin || (hasStrongQuoteIdentitySafe(asset) && (raw || storedYahoo || inferredYahoo || isPlausibleMarketTicker(raw, asset))));')
s=s.replace('sw.js?v=20260509v64','sw.js?v=20260509v65')
p.write_text(s)

# --- market.js: make Risk Budget readable and explanatory ---
p=root/'market.js'
s=p.read_text()
pattern=re.compile(r'''    const chips=\(items,limit\)=>items\.slice\(0,limit\)\.map\(x=>`<span><strong>\$\{esc\(x\.name\)\}</strong>\$\{x\.pct\.toFixed\(0\)\}%</span>`\)\.join\(''\);\n    const html=`<div class=\\?"market-detail-card market-risk-budget\\?">.*?\n    return \{fit,html,profile\};''',re.S)
m=pattern.search(s)
assert m, 'risk budget block not found'
new=r'''    const statusLabel=fit>=85?'Boa diversificação':fit>=65?'Atenção':'Concentração elevada';
    const riskRows=(items,limit,max)=>items.slice(0,limit).map(x=>{
      const over=x.pct>max, width=Math.max(2,Math.min(100,x.pct));
      return `<div class="market-risk-item ${over?'is-over':''}"><div class="market-risk-item__head"><strong>${esc(x.name)}</strong><span>${x.pct.toFixed(0)}%${over?` · limite ${max}%`:''}</span></div><div class="market-risk-bar"><i style="width:${width}%"></i></div></div>`;
    }).join('');
    const html=`<div class="market-detail-card market-risk-budget"><div class="market-perspective-head"><div><small>PORTFOLIO RISK BUDGET · PROXY</small><h4>Diversificação da carteira</h4></div><div class="market-risk-score ${tone}"><strong>${fit}/100</strong><small>${statusLabel}</small></div></div><p class="market-risk-intro">Mostra onde a carteira está mais dependente do mesmo fator, moeda ou região. Quanto maior a concentração, maior o impacto se esse risco correr mal.</p><div class="market-risk-grid"><section class="market-risk-group"><div class="market-risk-group__title"><strong>Fatores</strong><small>máx. ${maxFactor}%</small></div><div>${riskRows(profile.factors,5,maxFactor)||'<p class="market-risk-empty">Sem classificação suficiente.</p>'}</div></section><section class="market-risk-group"><div class="market-risk-group__title"><strong>Moedas</strong><small>máx. ${maxCurrency}%</small></div><div>${riskRows(profile.currencies,4,maxCurrency)||'<p class="market-risk-empty">Sem classificação suficiente.</p>'}</div></section><section class="market-risk-group"><div class="market-risk-group__title"><strong>Regiões</strong><small>máx. ${maxRegion}%</small></div><div>${riskRows(profile.regions,4,maxRegion)||'<p class="market-risk-empty">Sem classificação suficiente.</p>'}</div></section></div>${breaches.length?`<div class="market-risk-alert"><strong>${breaches.length} ${breaches.length===1?'excesso a acompanhar':'excessos a acompanhar'}</strong><ul>${breaches.slice(0,5).map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div>`:'<div class="market-risk-ok"><strong>Dentro dos limites definidos</strong><span>Não há concentrações acima dos teus Portfolio Targets.</span></div>'}<p class="market-risk-footnote">Leitura de exposição, não previsão de volatilidade. Usa os dados disponíveis e pode conter proxies quando moeda/região não vêm explicitamente da fonte.</p></div>`;
    return {fit,html,profile};'''
s=s[:m.start()]+new+s[m.end():]
p.write_text(s)

# --- market.css: readable mobile-first Risk Budget ---
p=root/'market.css'
css=p.read_text()
extra=r'''

/* v6.6.2 — Risk Budget readability */
.market-risk-budget{padding:16px}.market-risk-score{flex:0 0 auto;min-width:86px;border:1px solid var(--line);background:var(--card2);border-radius:15px;padding:8px 10px;text-align:center}.market-risk-score strong{display:block;font-size:18px;line-height:1.05}.market-risk-score small{display:block;margin-top:3px;font-size:9px;font-weight:800;color:var(--text2)}.market-risk-score.is-positive{background:rgba(73,180,103,.10);border-color:rgba(73,180,103,.24)}.market-risk-score.is-warn{background:rgba(210,174,101,.14);border-color:rgba(210,174,101,.30)}.market-risk-score.is-risk{background:rgba(229,88,77,.10);border-color:rgba(229,88,77,.22)}.market-risk-intro{font-size:12px!important;line-height:1.5!important;color:var(--text2)!important;margin:10px 0 4px}.market-risk-grid{display:grid;grid-template-columns:1fr;gap:10px;margin-top:10px}.market-risk-group{margin:0!important;padding:12px;border:1px solid var(--line2);background:var(--item-bg);border-radius:15px}.market-risk-group__title{display:flex!important;justify-content:space-between;align-items:center;gap:10px;margin-bottom:8px}.market-risk-group__title strong{font-size:13px}.market-risk-group__title small{font-size:10px!important;color:var(--muted)!important;margin:0!important}.market-risk-group>div:last-child{display:grid!important;gap:8px!important}.market-risk-item{display:block!important;border:0!important;background:transparent!important;border-radius:0!important;padding:0!important;color:var(--text)!important;font-size:12px!important}.market-risk-item__head{display:flex!important;justify-content:space-between;align-items:baseline;gap:10px}.market-risk-item__head strong{font-size:12px!important;color:var(--text)!important}.market-risk-item__head span{font-size:11px!important;color:var(--text2)!important;padding:0!important;border:0!important;background:transparent!important}.market-risk-item.is-over .market-risk-item__head span{color:#a2463e!important;font-weight:800}.market-risk-bar{height:7px;margin-top:5px;border-radius:999px;background:var(--line2);overflow:hidden}.market-risk-bar i{display:block;height:100%;border-radius:inherit;background:var(--vio)}.market-risk-item.is-over .market-risk-bar i{background:#c86b5e}.market-risk-alert,.market-risk-ok{margin-top:11px;border-radius:14px;padding:11px 12px}.market-risk-alert{background:rgba(229,88,77,.075);border:1px solid rgba(229,88,77,.16)}.market-risk-alert strong,.market-risk-ok strong{display:block;font-size:12px}.market-risk-alert ul{margin:6px 0 0;padding-left:17px}.market-risk-alert li{font-size:11px!important;line-height:1.45!important;color:var(--text2)!important}.market-risk-ok{background:rgba(73,180,103,.08);border:1px solid rgba(73,180,103,.15)}.market-risk-ok span{display:block;font-size:11px;color:var(--text2);margin-top:2px}.market-risk-footnote{font-size:10px!important;line-height:1.4!important;color:var(--muted)!important;margin-top:9px!important}.market-risk-empty{font-size:11px!important;color:var(--muted)!important;margin:0}
@media(min-width:600px){.market-risk-grid{grid-template-columns:repeat(3,1fr)}}
'''
if '/* v6.6.2 — Risk Budget readability */' not in css: css+=extra
p.write_text(css)

# --- README + cache ---
p=root/'README.md'; r=p.read_text()
if not r.startswith('## Vestra v6.6.2'):
    r='''## Vestra v6.6.2 — Risk Budget Clarity & Quote Refresh Repair\n\n- A box Diversificação real passa a usar blocos legíveis, barras de exposição, limites explícitos e uma leitura curta do score.\n- Excessos de fator/moeda/região ficam destacados sem depender de chips pequenos.\n- Corrige o erro `hasStrongQuoteIdentity is not defined` no caminho de atualização de cotações, preservando as proteções contra colisões de ticker e identidade fraca.\n- A mesma correção desbloqueia a atualização manual e o caminho automático que usa o mesmo motor de cotações ao abrir/regressar à app.\n- PWA cache: `vestra-cache-v65`.\n\n'''+r
p.write_text(r)
p=root/'sw.js'; sw=p.read_text().replace('vestra-cache-v64','vestra-cache-v65'); p.write_text(sw)
