from pathlib import Path

p=Path('market.js')
s=p.read_text()

old="""  function holdingWeight(h){
    let w=n(h?.weight??h?.holdingPercent??h?.holding_percent??h?.percent??h?.percentage);
    if(w==null) return null;
    if(Math.abs(w)<=1) w*=100;
    return w;
  }

  function portfolioAction(stock, alternativesByTicker){
"""
new="""  function holdingWeight(h){
    let w=n(h?.weight??h?.holdingPercent??h?.holding_percent??h?.percent??h?.percentage);
    if(w==null) return null;
    if(Math.abs(w)<=1) w*=100;
    return w;
  }

  function indirectExposurePct(stock, etfs){
    const symbol=txt(stock?.ticker).toUpperCase().replace(/\\.[A-Z]+$/,'');
    if(!symbol) return 0;
    let exposure=0;
    for(const e of etfs||[]){
      const portfolioWeight=n(e.portfolioPct)||0;
      for(const h of (e.stock?.top_holdings||[])){
        if(holdingSymbol(h)!==symbol) continue;
        const hw=holdingWeight(h);
        if(hw!=null) exposure += portfolioWeight*(hw/100);
      }
    }
    return exposure;
  }

  function portfolioFit(r, sectorRows, analysed, etfs){
    const positionPct=analysed>0?r.value/analysed*100:0;
    const sector=txt(r.stock?.sector)||'Sem setor';
    const sectorPct=sectorRows.find(x=>x.sector===sector)?.pct||0;
    const indirectPct=isFund(r.stock)?0:indirectExposurePct(r.stock,etfs);
    const flags=[];
    if(positionPct>=15) flags.push(`posição ${positionPct.toFixed(0)}%`);
    else if(positionPct>=10) flags.push(`posição já relevante ${positionPct.toFixed(0)}%`);
    if(sectorPct>=35) flags.push(`setor concentrado ${sectorPct.toFixed(0)}%`);
    else if(sectorPct>=28) flags.push(`setor já elevado ${sectorPct.toFixed(0)}%`);
    if(indirectPct>=2) flags.push(`+${indirectPct.toFixed(1)}% indireto via ETFs`);
    let fit='balanced';
    if(positionPct>=15||sectorPct>=35||indirectPct>=4) fit='concentrated';
    else if(positionPct>=10||sectorPct>=28||indirectPct>=2) fit='watch';
    return {positionPct,sectorPct,indirectPct,fit,flags};
  }

  function portfolioAction(stock, alternativesByTicker, context){
"""
if old not in s: raise SystemExit('anchor 1 not found')
s=s.replace(old,new,1)

old="""    const alt=alternativesByTicker?.get?.(txt(stock?.ticker).toUpperCase())||null;
    const reasons=[];
"""
new="""    const alt=alternativesByTicker?.get?.(txt(stock?.ticker).toUpperCase())||null;
    const ctx=context||{};
    const reasons=[];
"""
if old not in s: raise SystemExit('anchor 2 not found')
s=s.replace(old,new,1)

old="""    if(conf!=null&&conf<60) reasons.push('confiança limitada');
    if(alt && (gate==='high'||gate==='severe'||(conviction!=null&&conviction<50))) return {key:'replace',label:'Substituir',tone:'risk',reason:`${reasons[0]||'convicção fraca'} · alternativa ${alt.to.ticker} superior`};
    if(gate==='high'||gate==='severe'||thesis==='down'||estimates==='deteriorating'||(conviction!=null&&conviction<50)) return {key:'review',label:'Rever',tone:'risk',reason:reasons.slice(0,2).join(' · ')||'convicção baixa'};
    if(conviction!=null&&conviction>=70&&conf!=null&&conf>=60&&!['overvalued','uncertain'].includes(valuation)) return {key:'reinforce',label:'Reforçar',tone:'positive',reason:reasons.slice(0,2).join(' · ')||'convicção elevada'};
    return {key:'hold',label:'Manter',tone:'neutral',reason:reasons.slice(0,2).join(' · ')||'tese sem alteração material'};
"""
new="""    if(conf!=null&&conf<60) reasons.push('confiança limitada');
    if(ctx.indirectPct>=2) reasons.push(`overlap indireto ${ctx.indirectPct.toFixed(1)}%`);
    if(ctx.positionPct>=10) reasons.push(`peso ${ctx.positionPct.toFixed(0)}%`);
    if(ctx.sectorPct>=28) reasons.push(`setor ${ctx.sectorPct.toFixed(0)}%`);
    if(alt && alt.portfolioFit!=='worse' && (gate==='high'||gate==='severe'||(conviction!=null&&conviction<50))) {
      const fitNote=alt.portfolioFit==='better'?' · melhora diversificação':'';
      return {key:'replace',label:'Substituir',tone:'risk',reason:`${reasons[0]||'convicção fraca'} · alternativa ${alt.to.ticker} superior${fitNote}`};
    }
    if(gate==='high'||gate==='severe'||thesis==='down'||estimates==='deteriorating'||(conviction!=null&&conviction<50)) return {key:'review',label:'Rever',tone:'risk',reason:reasons.slice(0,2).join(' · ')||'convicção baixa'};
    if(conviction!=null&&conviction>=70&&conf!=null&&conf>=60&&!['overvalued','uncertain'].includes(valuation)) {
      if(ctx.fit==='concentrated') return {key:'hold',label:'Manter',tone:'neutral',reason:`boa tese · não reforçar por ${ctx.flags?.[0]||'concentração'}`};
      return {key:'reinforce',label:'Reforçar',tone:'positive',reason:reasons.slice(0,2).join(' · ')||'convicção elevada'};
    }
    return {key:'hold',label:'Manter',tone:'neutral',reason:reasons.slice(0,2).join(' · ')||'tese sem alteração material'};
"""
if old not in s: raise SystemExit('anchor 3 not found')
s=s.replace(old,new,1)

# attach portfolio weights to ETF rows before alternative selection
old="""    const weak=ranked.slice().sort((a,b)=>(a.conviction??999)-(b.conviction??999)).slice(0,5);
    const alternatives=[];
"""
new="""    const etfsForFit=ranked.filter(r=>isFund(r.stock)&&Array.isArray(r.stock.top_holdings)&&r.stock.top_holdings.length).map(r=>({...r,portfolioPct:r.value/analysed*100}));
    for(const r of ranked) r.portfolioFit=portfolioFit(r,sectorRows,analysed,etfsForFit);

    const weak=ranked.slice().sort((a,b)=>(a.conviction??999)-(b.conviction??999)).slice(0,5);
    const alternatives=[];
"""
if old not in s: raise SystemExit('anchor 4 not found')
s=s.replace(old,new,1)

old="""      const cand=M.stocks.filter(x=>!isFund(x)&&!heldTickers.has(txt(x.ticker).toUpperCase().replace(/\\.[A-Z]+$/,''))&&txt(x.sector)===txt(r.stock.sector)&&n(x.score)!=null&&n(x.score)>=curScore+8&&n(x.confidence_score)>=60&&!['high','severe'].includes(txt(x.risk_gate))&&txt(x.valuation_signal)!=='overvalued'&&txt(x.estimate_signal)!=='deteriorating')
        .sort((a,b)=>(portfolioConviction(b)||0)-(portfolioConviction(a)||0))[0];
      if(cand) alternatives.push({from:r.stock,to:cand,delta:n(cand.score)-curScore});
"""
new="""      const candidates=M.stocks.filter(x=>!isFund(x)&&!heldTickers.has(txt(x.ticker).toUpperCase().replace(/\\.[A-Z]+$/,''))&&txt(x.sector)===txt(r.stock.sector)&&n(x.score)!=null&&n(x.score)>=curScore+8&&n(x.confidence_score)>=60&&!['high','severe'].includes(txt(x.risk_gate))&&txt(x.valuation_signal)!=='overvalued'&&txt(x.estimate_signal)!=='deteriorating');
      const currentIndirect=r.portfolioFit?.indirectPct||0;
      const cand=candidates.map(x=>({stock:x,indirect:indirectExposurePct(x,etfsForFit)}))
        .sort((a,b)=>((portfolioConviction(b.stock)||0)-b.indirect*4)-((portfolioConviction(a.stock)||0)-a.indirect*4))[0];
      if(cand){
        const fit=cand.indirect+1<currentIndirect?'better':cand.indirect>currentIndirect+2?'worse':'neutral';
        alternatives.push({from:r.stock,to:cand.stock,delta:n(cand.stock.score)-curScore,portfolioFit:fit,currentIndirect,candidateIndirect:cand.indirect});
      }
"""
if old not in s: raise SystemExit('anchor 5 not found')
s=s.replace(old,new,1)

old="""    const actionRows=ranked.map(r=>({...r,action:portfolioAction(r.stock,alternativesByTicker)}));
"""
new="""    const actionRows=ranked.map(r=>({...r,action:portfolioAction(r.stock,alternativesByTicker,r.portfolioFit)}));
"""
if old not in s: raise SystemExit('anchor 6 not found')
s=s.replace(old,new,1)

old="""    const etfs=ranked.filter(r=>isFund(r.stock)&&Array.isArray(r.stock.top_holdings)&&r.stock.top_holdings.length);
"""
new="""    const etfs=etfsForFit;
"""
if old not in s: raise SystemExit('anchor 7 not found')
s=s.replace(old,new,1)

old="""    const altHtml=alternatives.length?`<div class=\"market-list\">${alternatives.map(a=>renderRow(a.to,`Alternativa a ${a.from.ticker} · Score +${a.delta.toFixed(0)} · mesmo setor`)).join('')}</div>`:'<p class=\"market-case-note\">Sem alternativa claramente superior identificada no mesmo setor.</p>';
"""
new="""    const altHtml=alternatives.length?`<div class=\"market-list\">${alternatives.map(a=>renderRow(a.to,`Alternativa a ${a.from.ticker} · Score +${a.delta.toFixed(0)} · ${a.portfolioFit==='better'?'reduz overlap':a.portfolioFit==='worse'?'aumenta overlap':'impacto neutro'}`)).join('')}</div>`:'<p class=\"market-case-note\">Sem alternativa claramente superior identificada no mesmo setor.</p>';
"""
if old not in s: raise SystemExit('anchor 8 not found')
s=s.replace(old,new,1)

old="""    const actionMapHtml=`<div class=\"market-detail-card market-action-map\"><div class=\"market-perspective-head\"><div><small>ACTION MAP</small><h4>Mapa da carteira</h4></div><span class=\"market-data-age\">${actionRows.length} posições</span></div><div class=\"market-action-summary\">"""
new="""    const concentratedCount=ranked.filter(r=>r.portfolioFit?.fit==='concentrated').length;
    const overlapCount=ranked.filter(r=>(r.portfolioFit?.indirectPct||0)>=2).length;
    const actionMapHtml=`<div class=\"market-detail-card market-action-map\"><div class=\"market-perspective-head\"><div><small>ACTION MAP · PORTFOLIO FIT</small><h4>Mapa da carteira</h4></div><span class=\"market-data-age\">${actionRows.length} posições</span></div><div class=\"market-action-context\"><span>${concentratedCount} concentração</span><span>${overlapCount} overlap indireto</span><span>${sectorRows[0]?`${esc(sectorRows[0].sector)} ${sectorRows[0].pct.toFixed(0)}%`:'setor —'}</span></div><div class=\"market-action-summary\">"""
if old not in s: raise SystemExit('anchor 9 not found')
s=s.replace(old,new,1)

# README and cache
p.write_text(s)

css=Path('market.css')
c=css.read_text()
c += "\n/* v5.0 — Portfolio Optimization Context */\n.market-action-context{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0 10px}.market-action-context span{font-size:9px;font-weight:800;color:var(--text2);background:var(--card2);border:1px solid var(--line);border-radius:999px;padding:5px 8px}\n"
css.write_text(c)

r=Path('README.md')
rt=r.read_text()
head="""## Vestra v5.0 — Portfolio Optimization Context

- O Portfolio Action Map passa a considerar o impacto de cada posição na carteira, não apenas a qualidade isolada do ativo.
- Peso da posição, concentração setorial e exposição indireta via ETFs entram no contexto de Reforçar / Manter / Rever / Substituir.
- Uma posição forte mas já demasiado grande deixa de ser candidata automática a reforço.
- Alternativas do mesmo setor são penalizadas quando aumentam overlap indireto e destacadas quando o reduzem.
- O mapa mostra indicadores de concentração e overlap antes das ações por posição.
- Continua a ser priorização de research, não uma ordem automática de transação.
- PWA cache: `vestra-cache-v45`.

"""
if not rt.startswith('## Vestra v5.0'):
    r.write_text(head+rt)

sw=Path('sw.js')
st=sw.read_text().replace('/* Vestra — Service Worker v4.9 */','/* Vestra — Service Worker v5.0 */').replace('vestra-cache-v44','vestra-cache-v45')
sw.write_text(st)
