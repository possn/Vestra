from pathlib import Path

p=Path('market.js')
s=p.read_text()

anchor='  function openTool(tool){\n'
if anchor not in s:
    raise SystemExit('openTool anchor not found')

insert=r'''  function portfolioConviction(s){
    const score=n(s?.score), conf=n(s?.confidence_score), est=n(s?.estimate_momentum_score);
    const valMap={undervalued:85,fair:65,overvalued:25,uncertain:40,insufficient:45};
    const val=valMap[txt(s?.valuation_signal)] ?? 50;
    const parts=[];
    if(score!=null) parts.push([score,.55]);
    if(conf!=null) parts.push([conf,.20]);
    if(est!=null) parts.push([est,.10]);
    parts.push([val,.15]);
    if(!parts.length) return null;
    let x=parts.reduce((a,[v,w])=>a+v*w,0)/parts.reduce((a,[,w])=>a+w,0);
    if(txt(s?.thesis_direction)==='up') x+=4;
    if(txt(s?.thesis_direction)==='down') x-=7;
    if(txt(s?.estimate_signal)==='deteriorating') x-=7;
    const gate=txt(s?.risk_gate);
    if(gate==='watch') x=Math.min(x,64);
    if(gate==='high') x=Math.min(x,49);
    if(gate==='severe') x=Math.min(x,35);
    return Math.max(0,Math.min(100,x));
  }

  function holdingSymbol(h){
    return txt(h?.symbol||h?.ticker||h?.holdingSymbol||h?.holding_symbol).toUpperCase().replace(/\.[A-Z]+$/,'');
  }
  function holdingWeight(h){
    let w=n(h?.weight??h?.holdingPercent??h?.holding_percent??h?.percent??h?.percentage);
    if(w==null) return null;
    if(Math.abs(w)<=1) w*=100;
    return w;
  }

  function portfolioIntelligence(rows,total){
    if(!rows.length) return '';
    const analysed=rows.reduce((a,r)=>a+r.value,0)||1;
    const ranked=rows.map(r=>({...r,conviction:portfolioConviction(r.stock)}));
    const heldTickers=new Set(ranked.map(r=>txt(r.stock.ticker).toUpperCase().replace(/\.[A-Z]+$/,'')));

    const sectors=new Map();
    for(const r of ranked){ const k=txt(r.stock.sector)||'Sem setor'; sectors.set(k,(sectors.get(k)||0)+r.value); }
    const sectorRows=[...sectors.entries()].map(([sector,value])=>({sector,value,pct:value/analysed*100})).sort((a,b)=>b.value-a.value);
    const topPosition=ranked.slice().sort((a,b)=>b.value-a.value)[0];
    const topPosPct=topPosition?topPosition.value/analysed*100:0;

    const reinforce=ranked.filter(r=>r.conviction!=null&&r.conviction>=70&&n(r.stock.confidence_score)>=60&&!['high','severe'].includes(txt(r.stock.risk_gate))&&!['overvalued','uncertain'].includes(txt(r.stock.valuation_signal))&&txt(r.stock.estimate_signal)!=='deteriorating')
      .sort((a,b)=>b.conviction-a.conviction).slice(0,3);
    const review=ranked.filter(r=>['high','severe'].includes(txt(r.stock.risk_gate))||txt(r.stock.thesis_direction)==='down'||txt(r.stock.estimate_signal)==='deteriorating'||(r.conviction!=null&&r.conviction<50))
      .sort((a,b)=>(a.conviction??999)-(b.conviction??999)).slice(0,3);

    const weak=ranked.slice().sort((a,b)=>(a.conviction??999)-(b.conviction??999)).slice(0,5);
    const alternatives=[];
    for(const r of weak){
      const curScore=n(r.stock.score); if(!txt(r.stock.sector)||curScore==null) continue;
      const cand=M.stocks.filter(x=>!isFund(x)&&!heldTickers.has(txt(x.ticker).toUpperCase().replace(/\.[A-Z]+$/,''))&&txt(x.sector)===txt(r.stock.sector)&&n(x.score)!=null&&n(x.score)>=curScore+8&&n(x.confidence_score)>=60&&!['high','severe'].includes(txt(x.risk_gate))&&txt(x.valuation_signal)!=='overvalued'&&txt(x.estimate_signal)!=='deteriorating')
        .sort((a,b)=>(portfolioConviction(b)||0)-(portfolioConviction(a)||0))[0];
      if(cand) alternatives.push({from:r.stock,to:cand,delta:n(cand.score)-curScore});
      if(alternatives.length>=3) break;
    }

    const overlaps=[];
    const etfs=ranked.filter(r=>isFund(r.stock)&&Array.isArray(r.stock.top_holdings)&&r.stock.top_holdings.length);
    for(let i=0;i<etfs.length;i++) for(let j=i+1;j<etfs.length;j++){
      const a=new Map(etfs[i].stock.top_holdings.map(h=>[holdingSymbol(h),holdingWeight(h)]).filter(([k,w])=>k&&w!=null));
      const b=new Map(etfs[j].stock.top_holdings.map(h=>[holdingSymbol(h),holdingWeight(h)]).filter(([k,w])=>k&&w!=null));
      let common=0, names=[];
      for(const [k,w] of a){ if(b.has(k)){ common+=Math.min(w,b.get(k)); names.push(k); } }
      if(common>=5) overlaps.push(`${etfs[i].stock.ticker} × ${etfs[j].stock.ticker} · ~${common.toFixed(0)}% top-holdings comuns${names.length?` (${names.slice(0,3).join(', ')})`:''}`);
    }
    for(const e of etfs){
      for(const h of e.stock.top_holdings){
        const sym=holdingSymbol(h), w=holdingWeight(h);
        if(sym&&w!=null&&w>=2&&heldTickers.has(sym)&&sym!==txt(e.stock.ticker).toUpperCase().replace(/\.[A-Z]+$/,'')) overlaps.push(`${sym} também está dentro de ${e.stock.ticker} · ~${w.toFixed(1)}% do ETF`);
      }
    }

    const concentration=[];
    if(topPosPct>=15) concentration.push(`${topPosition.stock.ticker} representa ~${topPosPct.toFixed(0)}% da parte analisável`);
    if(sectorRows[0]?.pct>=30) concentration.push(`${sectorRows[0].sector} concentra ~${sectorRows[0].pct.toFixed(0)}% da parte analisável`);
    concentration.push(...overlaps.slice(0,3));

    const compactRows=(arr,metaFn)=>arr.length?`<div class="market-list">${arr.map(r=>renderRow(r.stock,metaFn(r))).join('')}</div>`:'<p class="market-case-note">Nenhuma posição cumpre este filtro com os dados atuais.</p>';
    const altHtml=alternatives.length?`<div class="market-list">${alternatives.map(a=>renderRow(a.to,`Alternativa a ${a.from.ticker} · Score +${a.delta.toFixed(0)} · mesmo setor`)).join('')}</div>`:'<p class="market-case-note">Sem alternativa claramente superior identificada no mesmo setor.</p>';
    const concHtml=concentration.length?`<ul class="market-case-list">${[...new Set(concentration)].slice(0,5).map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'<p class="market-case-note">Sem concentração material detetada com os dados disponíveis.</p>';

    return `<div class="market-detail-card"><div class="market-perspective-head"><div><small>PORTFOLIO INTELLIGENCE</small><h4>Prioridades da carteira</h4></div><span class="market-data-age">${Math.round(analysed/(total||analysed)*100)}% coberto</span></div><p>Convicção combina Score Vestra, confiança, valuation, expectativas e Risk Gate. É uma priorização de research — não uma ordem de compra ou venda.</p></div>
      <div class="market-detail-card"><h4>Candidatos a reforço</h4>${compactRows(reinforce,r=>`Convicção ${Math.round(r.conviction)}/100 · ${txt(r.stock.valuation_signal)||'valuation sem sinal'}`)}</div>
      <div class="market-detail-card"><h4>Posições a rever</h4>${compactRows(review,r=>`Convicção ${r.conviction==null?'—':Math.round(r.conviction)}/100 · ${txt(r.stock.risk_gate)||'clear'} · ${txt(r.stock.estimate_signal)||'expectativas —'}`)}</div>
      <div class="market-detail-card"><h4>Concentração e overlap</h4>${concHtml}</div>
      <div class="market-detail-card"><h4>Alternativas no mesmo setor</h4><p class="market-case-note">Só aparecem quando há uma empresa não detida com score pelo menos 8 pontos superior, confiança ≥60 e sem Risk Gate alto/severo.</p>${altHtml}</div>`;
  }

'''
s=s.replace(anchor,insert+anchor,1)

needle='''          <div class="market-portfolio-summary"><div class="market-portfolio-kpi"><small>Posições</small><strong>${assets.length}</strong></div><div class="market-portfolio-kpi"><small>Com research</small><strong>${rows.length}</strong></div><div class="market-portfolio-kpi"><small>Cobertura</small><strong>${total>0?Math.round(analysed/total*100):0}%</strong></div></div>\n          <div class="market-portfolio-section">'''
repl='''          <div class="market-portfolio-summary"><div class="market-portfolio-kpi"><small>Posições</small><strong>${assets.length}</strong></div><div class="market-portfolio-kpi"><small>Com research</small><strong>${rows.length}</strong></div><div class="market-portfolio-kpi"><small>Cobertura</small><strong>${total>0?Math.round(analysed/total*100):0}%</strong></div></div>\n          ${portfolioIntelligence(rows,total)}\n          <div class="market-portfolio-section">'''
if needle not in s:
    raise SystemExit('portfolio summary anchor not found')
s=s.replace(needle,repl,1)
p.write_text(s)

# README
p=Path('README.md'); r=p.read_text()
block='''## Vestra v4.7 — Portfolio Intelligence\n\n- A área As minhas posições passa a incluir inteligência de carteira sem alterar a navegação global.\n- Convicção de research combina Score Vestra, Confidence Engine, valuation, estimate momentum e Risk Gate; permanece explicável e não é uma recomendação automática.\n- Novos blocos: candidatos a reforço, posições a rever, concentração/overlap e alternativas melhores no mesmo setor.\n- Overlap deteta concentração por posição/setor, holdings comuns entre ETFs e ações detidas diretamente que também aparecem dentro de ETFs.\n- Alternativas exigem score pelo menos 8 pontos superior, confiança >=60, mesmo setor e ausência de Risk Gate alto/severo.\n- Layout visual global permanece congelado.\n- PWA cache: `vestra-cache-v40`.\n\n'''
if not r.startswith('## Vestra v4.7'):
    p.write_text(block+r)

p=Path('sw.js'); w=p.read_text().replace('Service Worker v4.6','Service Worker v4.7').replace('vestra-cache-v39','vestra-cache-v40'); p.write_text(w)
