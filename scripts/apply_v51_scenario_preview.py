from pathlib import Path

p=Path('market.js')
s=p.read_text()

old="""    const altHtml=alternatives.length?`<div class=\"market-list\">${alternatives.map(a=>renderRow(a.to,`Alternativa a ${a.from.ticker} · Score +${a.delta.toFixed(0)} · ${a.portfolioFit==='better'?'reduz overlap':a.portfolioFit==='worse'?'aumenta overlap':'impacto neutro'}`)).join('')}</div>`:'<p class=\"market-case-note\">Sem alternativa claramente superior identificada no mesmo setor.</p>';
    const concHtml=concentration.length?`<ul class=\"market-case-list\">${[...new Set(concentration)].slice(0,5).map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'<p class=\"market-case-note\">Sem concentração material detetada com os dados disponíveis.</p>';

    const concentratedCount=ranked.filter(r=>r.portfolioFit?.fit==='concentrated').length;
"""
new="""    const altHtml=alternatives.length?`<div class=\"market-list\">${alternatives.map(a=>renderRow(a.to,`Alternativa a ${a.from.ticker} · Score +${a.delta.toFixed(0)} · ${a.portfolioFit==='better'?'reduz overlap':a.portfolioFit==='worse'?'aumenta overlap':'impacto neutro'}`)).join('')}</div>`:'<p class=\"market-case-note\">Sem alternativa claramente superior identificada no mesmo setor.</p>';
    const concHtml=concentration.length?`<ul class=\"market-case-list\">${[...new Set(concentration)].slice(0,5).map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'<p class=\"market-case-note\">Sem concentração material detetada com os dados disponíveis.</p>';

    const convRows=ranked.filter(r=>r.conviction!=null&&r.value>0);
    const convictionWeight=convRows.reduce((sum,r)=>sum+r.value,0)||1;
    const portfolioConvictionNow=convRows.reduce((sum,r)=>sum+r.value*r.conviction,0)/convictionWeight;
    const scenarioRows=alternatives.map(a=>{
      const fromRow=ranked.find(r=>txt(r.stock.ticker).toUpperCase()===txt(a.from.ticker).toUpperCase());
      if(!fromRow) return null;
      const oldConv=portfolioConviction(a.from), newConv=portfolioConviction(a.to);
      if(oldConv==null||newConv==null) return null;
      const w=fromRow.value/convictionWeight;
      const after=portfolioConvictionNow+(newConv-oldConv)*w;
      const overlapBefore=n(a.currentIndirect)||0, overlapAfter=n(a.candidateIndirect)||0;
      const convDelta=after-portfolioConvictionNow, overlapDelta=overlapAfter-overlapBefore;
      let impact='Neutro';
      if(convDelta>=.5||overlapDelta<=-1) impact='Melhora';
      if(convDelta<0||overlapDelta>=2) impact='Piora';
      return {from:a.from,to:a.to,before:portfolioConvictionNow,after,convDelta,overlapBefore,overlapAfter,overlapDelta,impact};
    }).filter(Boolean).slice(0,3);
    const scenarioHtml=scenarioRows.length?`<div class=\"market-detail-card market-scenario-preview\"><div class=\"market-perspective-head\"><div><small>SCENARIO PREVIEW</small><h4>Se substituíres pelo mesmo valor</h4></div><span class=\"market-data-age\">simulação</span></div><p class=\"market-case-note\">Mantém o valor da posição e o setor; estima apenas o efeito na convicção ponderada e no overlap indireto.</p><div class=\"market-scenario-list\">${scenarioRows.map(x=>`<div class=\"market-scenario-row\"><div><strong>${esc(x.from.ticker)} → ${esc(x.to.ticker)}</strong><small>Convicção carteira ${x.before.toFixed(1)} → ${x.after.toFixed(1)} · overlap ${x.overlapBefore.toFixed(1)}% → ${x.overlapAfter.toFixed(1)}%</small></div><em class=\"${x.impact==='Melhora'?'is-positive':x.impact==='Piora'?'is-risk':''}\">${x.impact}</em></div>`).join('')}</div></div>`:'';

    const concentratedCount=ranked.filter(r=>r.portfolioFit?.fit==='concentrated').length;
"""
if old not in s: raise SystemExit('anchor 1 not found')
s=s.replace(old,new,1)

old="""      <div class=\"market-detail-card\"><h4>Alternativas no mesmo setor</h4><p class=\"market-case-note\">Só aparecem quando há uma empresa não detida com score pelo menos 8 pontos superior, confiança ≥60 e sem Risk Gate alto/severo.</p>${altHtml}</div>`;
"""
new="""      <div class=\"market-detail-card\"><h4>Alternativas no mesmo setor</h4><p class=\"market-case-note\">Só aparecem quando há uma empresa não detida com score pelo menos 8 pontos superior, confiança ≥60 e sem Risk Gate alto/severo.</p>${altHtml}</div>
      ${scenarioHtml}`;
"""
if old not in s: raise SystemExit('anchor 2 not found')
s=s.replace(old,new,1)
p.write_text(s)

css=Path('market.css')
c=css.read_text()+"\n/* v5.1 — Portfolio Scenario Preview */\n.market-scenario-list{display:grid;gap:7px;margin-top:10px}.market-scenario-row{display:flex;justify-content:space-between;gap:10px;align-items:center;border:1px solid var(--line2);background:var(--item-bg);border-radius:14px;padding:10px 11px}.market-scenario-row strong{display:block;font-size:12px}.market-scenario-row small{display:block;color:var(--text2);font-size:10px;line-height:1.35;margin-top:2px}.market-scenario-row em{font-style:normal;flex:0 0 auto;font-size:9px;font-weight:900;padding:5px 8px;border-radius:999px;background:var(--card2);border:1px solid var(--line);color:var(--text2)}.market-scenario-row em.is-positive{background:rgba(73,180,103,.12);color:#34764a}.market-scenario-row em.is-risk{background:rgba(229,88,77,.10);color:#9b4b44}\n"
css.write_text(c)

r=Path('README.md')
rt=r.read_text()
head="""## Vestra v5.1 — Portfolio Scenario Preview

- As substituições sugeridas passam a mostrar um preview antes/depois mantendo o mesmo valor da posição.
- A simulação estima a alteração da convicção ponderada da carteira e do overlap indireto via ETFs.
- Como as alternativas são do mesmo setor, a concentração setorial é assumida como inalterada nesta primeira versão.
- Cada cenário é marcado como Melhora / Neutro / Piora e continua a ser apenas apoio a research.
- PWA cache: `vestra-cache-v46`.

"""
if not rt.startswith('## Vestra v5.1'):
    r.write_text(head+rt)

sw=Path('sw.js')
st=sw.read_text().replace('/* Vestra — Service Worker v5.0 */','/* Vestra — Service Worker v5.1 */').replace('vestra-cache-v45','vestra-cache-v46')
sw.write_text(st)
