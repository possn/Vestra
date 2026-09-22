/* Vestra Dashboard Portfolio Concentration v1.0 — direct-holdings concentration, no ETF look-through. */
(() => {
  'use strict';

  const CARD_ID='dashboardPortfolioConcentrationCard';
  const STYLE_ID='dashboardPortfolioConcentrationStyle';
  const MAX_SEGMENTS=6;
  const text=v=>String(v??'').trim();
  const num=v=>{const n=Number(v);return Number.isFinite(n)?n:null;};

  function getState(){try{return (typeof state!=='undefined'&&state)?state:null;}catch{return null;}}
  function directHoldings(){
    const assets=Array.isArray(getState()?.assets)?getState().assets:[];
    return assets.map((asset,index)=>{
      const value=num(asset?.value ?? asset?.currentValue ?? asset?.marketValue);
      const label=text(asset?.ticker||asset?.symbol||asset?.name)||`Posição ${index+1}`;
      return {asset,label,value};
    }).filter(x=>x.value!=null&&x.value>0).sort((a,b)=>b.value-a.value);
  }

  function concentrationSnapshot(rows=directHoldings()){
    const total=rows.reduce((sum,row)=>sum+row.value,0);
    if(!(total>0)) return {total:0,count:0,top1:null,top3:null,effective:null,rows:[]};
    const weighted=rows.map(row=>({...row,weight:row.value/total}));
    const top1=weighted[0]?.weight ?? null;
    const top3=weighted.slice(0,3).reduce((sum,row)=>sum+row.weight,0);
    const hhi=weighted.reduce((sum,row)=>sum+row.weight*row.weight,0);
    const effective=hhi>0?1/hhi:null;
    return {total,count:weighted.length,top1,top3,effective,rows:weighted};
  }

  function pct(v){return v==null?'—':`${(v*100).toLocaleString('pt-PT',{maximumFractionDigits:1})}%`;}
  function effective(v){return v==null?'—':v.toLocaleString('pt-PT',{maximumFractionDigits:1});}

  function ensureStyles(){
    if(document.getElementById(STYLE_ID)) return;
    const link=document.createElement('link');
    link.id=STYLE_ID; link.rel='stylesheet'; link.href='dashboard-portfolio-concentration.css?v=1.0';
    document.head.appendChild(link);
  }

  function segmentMarkup(rows){
    const shown=rows.slice(0,MAX_SEGMENTS);
    const rest=rows.slice(MAX_SEGMENTS).reduce((sum,row)=>sum+row.weight,0);
    const items=[...shown];
    if(rest>0) items.push({label:'Outras',weight:rest});
    return items.map((row,index)=>`<div class="dpc-segment dpc-segment--${(index%5)+1}" style="flex:${Math.max(row.weight,.04)} 1 0" title="${text(row.label)} · ${pct(row.weight)}"><span>${text(row.label)}</span><strong>${pct(row.weight)}</strong></div>`).join('');
  }

  function markup(snapshot){
    if(!snapshot.count) return `<section class="dpc-card" id="${CARD_ID}"><div class="dpc-head"><div><span class="dpc-kicker">CONCENTRAÇÃO DIRETA</span><h3>Quanto depende das maiores posições?</h3></div></div><div class="dpc-empty">Adiciona posições à carteira para calcular a concentração direta.</div></section>`;
    return `<section class="dpc-card" id="${CARD_ID}">
      <div class="dpc-head"><div><span class="dpc-kicker">CONCENTRAÇÃO DIRETA</span><h3>Quanto depende das maiores posições?</h3><p>Leitura simples do peso das posições individuais, sem inferir temas ou exposição interna de ETFs.</p></div></div>
      <div class="dpc-metrics">
        <div><span>Maior posição</span><strong>${pct(snapshot.top1)}</strong></div>
        <div><span>Top 3</span><strong>${pct(snapshot.top3)}</strong></div>
        <div><span>Posições efetivas</span><strong>${effective(snapshot.effective)}</strong><small>1 / HHI</small></div>
      </div>
      <div class="dpc-mosaic" aria-label="Peso das maiores posições">${segmentMarkup(snapshot.rows)}</div>
      <div class="dpc-foot">Cobertura: ${snapshot.count} posições diretas · ETFs contam como uma posição única. O look-through por holdings será uma camada separada para evitar dupla contagem.</div>
    </section>`;
  }

  function mount(){
    const dashboard=document.getElementById('viewDashboard');
    if(!dashboard) return null;
    const anchor=document.getElementById('dashboardPortfolioPulseCard')||dashboard.querySelector('.kpi-quick');
    return {dashboard,anchor};
  }

  function render(){
    ensureStyles();
    const target=mount(); if(!target) return false;
    const shell=document.createElement('div'); shell.innerHTML=markup(concentrationSnapshot());
    const next=shell.firstElementChild; if(!next) return false;
    const existing=document.getElementById(CARD_ID);
    if(existing) existing.replaceWith(next);
    else if(target.anchor) target.anchor.insertAdjacentElement('afterend',next);
    else target.dashboard.appendChild(next);
    return true;
  }

  function boot(){
    render();
    window.addEventListener('vestra:app-ready',render);
    window.addEventListener('vestra:market-ready',render);
    document.addEventListener('click',event=>{if(event.target?.closest?.('[data-view="dashboard"]'))setTimeout(render,60);});
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot,{once:true}); else boot();

  window.VestraDashboardPortfolioConcentration=Object.freeze({version:'1.0',directHoldings,concentrationSnapshot,render});
})();