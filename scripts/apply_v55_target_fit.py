from pathlib import Path

p=Path('market.js')
s=p.read_text()
old="""    const targets=loadPortfolioTargets();
    const targetHtml=`<div class=\"market-detail-card market-target-engine\" data-target-engine>"""
new="""    const targets=loadPortfolioTargets();
    const targetPositionBreaches=ranked.map(r=>({ticker:r.stock.ticker,pct:r.value/analysed*100})).filter(x=>x.pct>targets.maxPosition).sort((a,b)=>b.pct-a.pct);
    const targetSectorBreaches=sectorRows.filter(x=>x.pct>targets.maxSector);
    const targetOverlapBreaches=targets.overlap==='reduce'?ranked.filter(r=>(r.portfolioFit?.indirectPct||0)>=2):[];
    const posExcess=targetPositionBreaches.reduce((a,x)=>a+(x.pct-targets.maxPosition),0);
    const sectorExcess=targetSectorBreaches.reduce((a,x)=>a+(x.pct-targets.maxSector),0);
    const overlapExcess=targetOverlapBreaches.reduce((a,r)=>a+Math.max(0,(r.portfolioFit?.indirectPct||0)-2),0);
    const targetFit=Math.max(0,Math.min(100,Math.round(100-posExcess*1.5-sectorExcess*1.15-overlapExcess*2.5)));
    const targetTone=targetFit>=85?'is-positive':targetFit>=65?'is-warn':'is-risk';
    const targetIssues=[];
    targetPositionBreaches.slice(0,3).forEach(x=>targetIssues.push(`${x.ticker} ${x.pct.toFixed(1)}% > objetivo ${targets.maxPosition}%`));
    targetSectorBreaches.slice(0,2).forEach(x=>targetIssues.push(`${x.sector} ${x.pct.toFixed(1)}% > objetivo ${targets.maxSector}%`));
    if(targetOverlapBreaches.length) targetIssues.push(`${targetOverlapBreaches.length} posições com overlap indireto ≥2%`);
    const targetFitHtml=`<div class=\"market-detail-card market-target-fit\"><div class=\"market-perspective-head\"><div><small>TARGET FIT</small><h4>Aderência aos objetivos</h4></div><span class=\"market-target-fit-score ${targetTone}\">${targetFit}/100</span></div><div class=\"market-action-context\"><span>${targetPositionBreaches.length} posições acima</span><span>${targetSectorBreaches.length} setores acima</span><span>${targetOverlapBreaches.length} overlap</span></div>${targetIssues.length?`<ul class=\"market-case-list\">${targetIssues.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'<p class=\"market-case-note\">A parte analisável da carteira está dentro dos objetivos definidos.</p>'}</div>`;
    const targetHtml=`<div class=\"market-detail-card market-target-engine\" data-target-engine>"""
if old not in s: raise SystemExit('anchor1 missing')
s=s.replace(old,new,1)
old2="""      ${scenarioHtml}
      ${targetHtml}
      ${rebalancerHtml}
"""
new2="""      ${scenarioHtml}
      ${targetFitHtml}
      ${targetHtml}
      ${rebalancerHtml}
"""
if old2 not in s: raise SystemExit('anchor2 missing')
s=s.replace(old2,new2,1)
p.write_text(s)

p=Path('market.css'); c=p.read_text()+"""

/* v5.5 — Target Fit & Drift */
.market-target-fit-score{font-size:13px;font-weight:950;padding:6px 9px;border-radius:10px;background:var(--card2);border:1px solid var(--line)}.market-target-fit-score.is-positive{color:#34764a;background:rgba(73,180,103,.10)}.market-target-fit-score.is-warn{color:#7d6734;background:rgba(210,174,101,.13)}.market-target-fit-score.is-risk{color:#9b4b44;background:rgba(229,88,77,.10)}
"""; p.write_text(c)

p=Path('README.md'); r=p.read_text(); r="""## Vestra v5.5 — Target Fit & Drift

- Novo Target Fit 0–100 na Portfolio Intelligence para medir aderência aos objetivos definidos na v5.4.
- Identifica posições acima do peso máximo, setores acima do limite e overlap indireto relevante quando o objetivo é reduzi-lo.
- Mostra os principais desvios em linguagem simples, antes do painel de configuração e do rebalanceador.
- O score de aderência é de construção de carteira e não altera o Score Vestra das empresas.
- PWA cache: `vestra-cache-v50`.

"""+r; p.write_text(r)

p=Path('sw.js'); w=p.read_text().replace('Service Worker v5.4','Service Worker v5.5').replace('vestra-cache-v49','vestra-cache-v50'); p.write_text(w)
