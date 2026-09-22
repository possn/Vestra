/* Vestra Dashboard Portfolio Concentration v1.1 — direct + evidence-based ETF look-through. */
(() => {
  'use strict';

  const CARD_ID='dashboardPortfolioConcentrationCard';
  const STYLE_ID='dashboardPortfolioConcentrationStyle';
  const MAX_SEGMENTS=6;
  const S={mode:'direct',lookthrough:null,loading:false,scheduled:false};
  const text=v=>String(v??'').trim();
  const esc=v=>text(v).replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const num=v=>{const n=Number(v);return Number.isFinite(n)?n:null;};

  function getState(){try{return (typeof state!=='undefined'&&state)?state:null;}catch{return null;}}
  function assetValue(asset){return num(asset?.value ?? asset?.currentValue ?? asset?.marketValueEUR ?? asset?.marketValue);}
  function assetTicker(asset){return text(asset?.yahooTicker||asset?.ticker||asset?.symbol).toUpperCase();}
  function isFundAsset(asset){
    const cls=text(asset?.class).toLowerCase();
    return cls.includes('etf')||cls.includes('fund');
  }

  function directHoldings(){
    const assets=Array.isArray(getState()?.assets)?getState().assets:[];
    return assets.map((asset,index)=>{
      const value=assetValue(asset);
      const label=text(asset?.ticker||asset?.symbol||asset?.name)||`Posição ${index+1}`;
      return {asset,label,value};
    }).filter(x=>x.value!=null&&x.value>0).sort((a,b)=>b.value-a.value);
  }

  function concentrationSnapshot(rows=directHoldings()){
    const total=rows.reduce((sum,row)=>sum+row.value,0);
    if(!(total>0)) return {total:0,count:0,top1:null,top3:null,effective:null,rows:[]};
    const weighted=rows.map(row=>({...row,weight:row.value/total})).sort((a,b)=>b.weight-a.weight);
    const top1=weighted[0]?.weight ?? null;
    const top3=weighted.slice(0,3).reduce((sum,row)=>sum+row.weight,0);
    const hhi=weighted.reduce((sum,row)=>sum+row.weight*row.weight,0);
    const effective=hhi>0?1/hhi:null;
    return {total,count:weighted.length,top1,top3,effective,rows:weighted};
  }

  function ratioToFraction(v){
    const x=num(v);
    if(x==null||x<0) return null;
    return x>1 ? x/100 : x;
  }

  function holdingIdentity(holding,index){
    const ticker=text(holding?.symbol||holding?.ticker||holding?.holdingSymbol||holding?.holdingTicker).toUpperCase();
    const name=text(holding?.holdingName||holding?.name||holding?.longName||holding?.shortName);
    const key=ticker ? `ticker:${ticker}` : name ? `name:${name.toLowerCase()}` : `unknown:${index}`;
    return {key,label:ticker||name||`Holding ${index+1}`};
  }

  function holdingFraction(holding){
    return ratioToFraction(holding?.holdingPercent ?? holding?.weight ?? holding?.pct ?? holding?.percentage);
  }

  function buildLookthrough(assets,detailsByTicker={}){
    const rows=Array.isArray(assets)?assets:[];
    const total=rows.reduce((sum,asset)=>sum+(assetValue(asset)||0),0);
    if(!(total>0)) return {total:0,count:0,rows:[],etfCount:0,coveredEtfs:0,etfCoverage:null,knownUnderlyingWeight:0};

    const exposures=new Map();
    let etfValue=0, knownEtfValue=0, etfCount=0, coveredEtfs=0, knownUnderlyingValue=0;
    const add=(key,label,value,kind='direct')=>{
      if(!(value>0)) return;
      const prev=exposures.get(key);
      if(prev){prev.value+=value; if(prev.kind!==kind) prev.kind='overlap';}
      else exposures.set(key,{key,label,value,kind});
    };

    rows.forEach((asset,assetIndex)=>{
      const value=assetValue(asset);
      if(!(value>0)) return;
      const ticker=assetTicker(asset);
      if(!isFundAsset(asset)){
        const label=ticker||text(asset?.name)||`Posição ${assetIndex+1}`;
        add(ticker?`ticker:${ticker}`:`direct:${assetIndex}`,label,value,'direct');
        return;
      }

      etfCount+=1; etfValue+=value;
      const detail=detailsByTicker[ticker]||null;
      const holdings=Array.isArray(detail?.top_holdings)?detail.top_holdings:[];
      const parsed=holdings.map((holding,index)=>{
        const fraction=holdingFraction(holding);
        return fraction!=null&&fraction>0 ? {...holdingIdentity(holding,index),fraction} : null;
      }).filter(Boolean);
      const rawCoverage=parsed.reduce((sum,row)=>sum+row.fraction,0);
      const valid=parsed.length>0&&rawCoverage>0&&rawCoverage<=1.05;

      if(!valid){
        add(`etf:${ticker||assetIndex}:unknown`,`${ticker||text(asset?.name)||'ETF'} · não detalhado`,value,'unknown-etf');
        return;
      }

      const scale=rawCoverage>1 ? 1/rawCoverage : 1;
      const covered=Math.min(1,rawCoverage*scale);
      coveredEtfs+=1; knownEtfValue+=value;
      for(const holding of parsed){
        const fraction=holding.fraction*scale;
        const contribution=value*fraction;
        add(holding.key,holding.label,contribution,'etf-holding');
        knownUnderlyingValue+=contribution;
      }
      const residual=Math.max(0,1-covered);
      if(residual>.001) add(`etf:${ticker||assetIndex}:residual`,`${ticker||text(asset?.name)||'ETF'} · restante`,value*residual,'etf-residual');
    });

    const exposureRows=[...exposures.values()].sort((a,b)=>b.value-a.value);
    const snapshot=concentrationSnapshot(exposureRows);
    return {
      ...snapshot,
      etfCount,
      coveredEtfs,
      etfCoverage:etfValue>0?knownEtfValue/etfValue:null,
      knownUnderlyingWeight:knownUnderlyingValue/total,
    };
  }

  function pct(v){return v==null?'—':`${(v*100).toLocaleString('pt-PT',{maximumFractionDigits:1})}%`;}
  function effective(v){return v==null?'—':v.toLocaleString('pt-PT',{maximumFractionDigits:1});}

  function ensureStyles(){
    if(document.getElementById(STYLE_ID)) return;
    const link=document.createElement('link');
    link.id=STYLE_ID; link.rel='stylesheet'; link.href='dashboard-portfolio-concentration.css?v=1.1';
    document.head.appendChild(link);
  }

  function segmentMarkup(rows){
    const shown=rows.slice(0,MAX_SEGMENTS);
    const rest=rows.slice(MAX_SEGMENTS).reduce((sum,row)=>sum+row.weight,0);
    const items=[...shown];
    if(rest>0) items.push({label:'Outras',weight:rest,kind:'other'});
    return items.map((row,index)=>`<div class="dpc-segment dpc-segment--${(index%5)+1}" style="flex:${Math.max(row.weight,.04)} 1 0" title="${esc(row.label)} · ${pct(row.weight)}"><span>${esc(row.label)}</span><strong>${pct(row.weight)}</strong></div>`).join('');
  }

  function metrics(snapshot){
    return `<div class="dpc-metrics">
      <div><span>Maior exposição</span><strong>${pct(snapshot.top1)}</strong></div>
      <div><span>Top 3</span><strong>${pct(snapshot.top3)}</strong></div>
      <div><span>Posições efetivas</span><strong>${effective(snapshot.effective)}</strong><small>1 / HHI</small></div>
    </div>`;
  }

  function modeToggle(hasEtfs){
    if(!hasEtfs) return '';
    return `<div class="dpc-mode" role="group" aria-label="Modo de concentração">
      <button type="button" data-dpc-mode="direct" class="${S.mode==='direct'?'is-active':''}">Direta</button>
      <button type="button" data-dpc-mode="lookthrough" class="${S.mode==='lookthrough'?'is-active':''}">Look-through ETF</button>
    </div>`;
  }

  function markup(direct){
    if(!direct.count) return `<section class="dpc-card" id="${CARD_ID}"><div class="dpc-head"><div><span class="dpc-kicker">CONCENTRAÇÃO</span><h3>Quanto da carteira é realmente a mesma aposta?</h3></div></div><div class="dpc-empty">Adiciona posições à carteira para calcular a concentração.</div></section>`;

    const fundCount=direct.rows.filter(row=>isFundAsset(row.asset)).length;
    const usingLookthrough=S.mode==='lookthrough'&&fundCount>0;
    const snapshot=usingLookthrough&&S.lookthrough?S.lookthrough:direct;
    const description=usingLookthrough
      ? 'Ações diretas e holdings conhecidas dos ETFs são agregadas pela identidade disponível. O restante de cada ETF fica explícito, sem o inventar.'
      : 'Peso das posições individuais. Usa Look-through ETF para revelar sobreposição quando existem holdings verificáveis.';
    const status=usingLookthrough
      ? S.loading
        ? '<div class="dpc-status">A carregar holdings dos ETFs…</div>'
        : S.lookthrough
          ? `<div class="dpc-status">Cobertura ETF ${pct(S.lookthrough.etfCoverage)} · exposição subjacente identificada ${pct(S.lookthrough.knownUnderlyingWeight)}</div>`
          : '<div class="dpc-status">Ainda sem holdings suficientes para look-through.</div>'
      : '';

    return `<section class="dpc-card" id="${CARD_ID}">
      <div class="dpc-head"><div><span class="dpc-kicker">CONCENTRAÇÃO</span><h3>Quanto da carteira é realmente a mesma aposta?</h3><p>${description}</p></div></div>
      ${modeToggle(fundCount>0)}
      ${metrics(snapshot)}
      <div class="dpc-mosaic" aria-label="Peso das maiores exposições">${segmentMarkup(snapshot.rows)}</div>
      ${status}
      <div class="dpc-foot">${usingLookthrough ? 'Sem dupla contagem: cada euro de ETF é repartido pelas holdings conhecidas e por um bloco residual explícito. Não há inferência temática nesta fase.' : `Cobertura direta: ${snapshot.count} posições · ETFs contam como uma posição única neste modo.`}</div>
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

  async function hydrateLookthrough(force=false){
    if(S.loading) return S.lookthrough;
    const assets=(Array.isArray(getState()?.assets)?getState().assets:[]).filter(asset=>assetValue(asset)>0);
    const funds=assets.filter(isFundAsset).filter(asset=>assetTicker(asset));
    if(!funds.length){S.lookthrough=null;render();return null;}
    if(S.lookthrough&&!force){render();return S.lookthrough;}
    S.loading=true;render();
    const details={};
    try{
      await window.VestraMarketLoader?.ensureHelpers?.();
      const hydrate=window.VestraMarketData?.hydrateTicker;
      if(typeof hydrate==='function'){
        const settled=await Promise.allSettled(funds.map(asset=>hydrate(assetTicker(asset))));
        settled.forEach((row,index)=>{if(row.status==='fulfilled'&&row.value)details[assetTicker(funds[index])]=row.value;});
      }
      S.lookthrough=buildLookthrough(assets,details);
    }catch(_){
      S.lookthrough=buildLookthrough(assets,details);
    }finally{
      S.loading=false;render();
    }
    return S.lookthrough;
  }

  function scheduleLookthrough(){
    if(S.scheduled) return;
    const assets=Array.isArray(getState()?.assets)?getState().assets:[];
    if(!assets.some(isFundAsset)) return;
    S.scheduled=true;
    const run=()=>{S.scheduled=false;void hydrateLookthrough(false);};
    if(typeof requestIdleCallback==='function') requestIdleCallback(run,{timeout:2200});
    else setTimeout(run,1200);
  }

  function boot(){
    render(); scheduleLookthrough();
    window.addEventListener('vestra:app-ready',()=>{S.lookthrough=null;render();scheduleLookthrough();});
    window.addEventListener('vestra:market-ready',()=>{render();scheduleLookthrough();});
    const net=document.getElementById('kpiNet');
    if(net&&typeof MutationObserver==='function'){
      const observer=new MutationObserver(()=>{S.lookthrough=null;render();scheduleLookthrough();});
      observer.observe(net,{childList:true,subtree:true,characterData:true});
    }
    document.addEventListener('click',event=>{
      const mode=event.target?.closest?.('[data-dpc-mode]')?.dataset?.dpcMode;
      if(mode==='direct'||mode==='lookthrough'){
        S.mode=mode;
        render();
        if(mode==='lookthrough') void hydrateLookthrough(false);
        return;
      }
      if(event.target?.closest?.('[data-view="dashboard"]')) setTimeout(()=>{render();scheduleLookthrough();},60);
    });
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot,{once:true}); else boot();

  window.VestraDashboardPortfolioConcentration=Object.freeze({
    version:'1.1',directHoldings,concentrationSnapshot,buildLookthrough,hydrateLookthrough,render
  });
})();