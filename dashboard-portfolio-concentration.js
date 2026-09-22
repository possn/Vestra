/* Vestra Portfolio Concentration v1.4 — portfolio-owned direct, ETF look-through + explainable thematic exposure. */
(() => {
  'use strict';

  const CARD_ID='dashboardPortfolioConcentrationCard';
  const STYLE_ID='dashboardPortfolioConcentrationStyle';
  const MAX_SEGMENTS=6;
  const S={mode:'direct',lookthrough:null,themes:null,details:{},selectedTheme:'',loading:false,scheduled:false};
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

  const THEME_RULES=[
    ['Semicondutores', s => /semiconductor|chip|microprocessor|integrated circuit/i.test(s.text)],
    ['IA & Robótica', s => /artificial intelligence|machine learning|robotics|robotic|automation/i.test(s.text)],
    ['Cibersegurança', s => /cybersecurity|cyber security|information security|network security/i.test(s.text)],
    ['Biotecnologia', s => /biotech|biotechnology|biopharma|biopharmaceutical/i.test(s.text)],
    ['Defesa & Aeroespacial', s => /aerospace|defen[cs]e|military/i.test(s.text)],
    ['Energia limpa', s => /renewable|solar|wind energy|clean energy|hydrogen|fuel cell/i.test(s.text)],
    ['Nuclear & Urânio', s => /nuclear|uranium/i.test(s.text)],
    ['Água', s => /water|wastewater|desalination/i.test(s.text)],
    ['Agricultura', s => /agricultur|farm|fertili[sz]er|crop|seed|grain/i.test(s.text)],
    ['Imobiliário', s => s.sector==='Real Estate'||/reit|real estate/i.test(s.text)],
    ['Tecnologia', s => s.sector==='Technology'],
    ['Saúde', s => s.sector==='Healthcare'],
    ['Financeiro', s => s.sector==='Financial Services'],
    ['Indústria', s => s.sector==='Industrials'],
    ['Energia', s => s.sector==='Energy'],
    ['Consumo', s => /^Consumer /.test(s.sector)],
    ['Utilities', s => s.sector==='Utilities'],
    ['Materiais', s => s.sector==='Basic Materials'],
  ];

  function themeEvidence(row){
    if(!row) return null;
    const sector=text(row?.sector);
    const blob=[row?.sector,row?.industry,row?.category,row?.theme,row?.stock_theme,row?.style,row?.description,row?.long_business_summary,row?.business_summary].map(text).join(' ');
    if(!sector&&!blob) return null;
    return {sector,text:blob};
  }

  function primaryTheme(row){
    const evidence=themeEvidence(row);
    if(!evidence) return null;
    const found=THEME_RULES.find(([,match])=>match(evidence));
    return found?.[0]||null;
  }

  function universeByTicker(stocks){
    const map=new Map();
    for(const row of Array.isArray(stocks)?stocks:[]){
      const ticker=text(row?.ticker).toUpperCase();
      if(ticker&&!map.has(ticker)) map.set(ticker,row);
    }
    return map;
  }

  function buildThemeExposure(assets,detailsByTicker={},stocks=[]){
    const rows=Array.isArray(assets)?assets:[];
    const total=rows.reduce((sum,asset)=>sum+(assetValue(asset)||0),0);
    if(!(total>0)) return {total:0,coverage:null,rows:[],classifiedValue:0};
    const byTicker=universeByTicker(stocks);
    const buckets=new Map();
    let classifiedValue=0;

    const add=(theme,value,contributor='')=>{
      if(!(value>0)) return;
      const label=theme||'Não classificado';
      const bucket=buckets.get(label)||{value:0,contributors:new Map()};
      bucket.value+=value;
      const key=text(contributor)||'Exposição sem identificação';
      bucket.contributors.set(key,(bucket.contributors.get(key)||0)+value);
      buckets.set(label,bucket);
      if(theme) classifiedValue+=value;
    };
    const resolve=(ticker,fallback=null)=>detailsByTicker[ticker]||byTicker.get(ticker)||fallback||null;

    rows.forEach((asset,assetIndex)=>{
      const value=assetValue(asset);
      if(!(value>0)) return;
      const ticker=assetTicker(asset);
      if(!isFundAsset(asset)){
        add(primaryTheme(resolve(ticker,asset)),value,ticker||text(asset?.name)||`Posição ${assetIndex+1}`);
        return;
      }

      const detail=detailsByTicker[ticker]||null;
      const holdings=Array.isArray(detail?.top_holdings)?detail.top_holdings:[];
      const parsed=holdings.map((holding,index)=>{
        const fraction=holdingFraction(holding);
        if(fraction==null||fraction<=0) return null;
        const identity=holdingIdentity(holding,index);
        const holdingTicker=text(holding?.symbol||holding?.ticker||holding?.holdingSymbol||holding?.holdingTicker).toUpperCase();
        const evidence=resolve(holdingTicker,holding);
        return {...identity,fraction,theme:primaryTheme(evidence)};
      }).filter(Boolean);
      const rawCoverage=parsed.reduce((sum,row)=>sum+row.fraction,0);
      const valid=parsed.length>0&&rawCoverage>0&&rawCoverage<=1.05;
      if(!valid){ add(null,value,ticker||text(asset?.name)||'ETF'); return; }

      const scale=rawCoverage>1?1/rawCoverage:1;
      let allocated=0;
      for(const holding of parsed){
        const contribution=value*holding.fraction*scale;
        allocated+=contribution;
        add(holding.theme,contribution,`${ticker||text(asset?.name)||'ETF'} → ${holding.label}`);
      }
      const residual=Math.max(0,value-allocated);
      if(residual>.01) add(null,residual,`${ticker||text(asset?.name)||'ETF'} → restante`);
    });

    const themeRows=[...buckets.entries()].map(([label,bucket])=>({
      label,
      value:bucket.value,
      weight:bucket.value/total,
      kind:label==='Não classificado'?'unclassified':'theme',
      contributors:[...bucket.contributors.entries()].map(([name,value])=>({name,value,weight:value/total})).sort((a,b)=>b.value-a.value),
    })).sort((a,b)=>b.value-a.value);
    return {total,coverage:classifiedValue/total,rows:themeRows,classifiedValue};
  }

  function pct(v){return v==null?'—':`${(v*100).toLocaleString('pt-PT',{maximumFractionDigits:1})}%`;}
  function effective(v){return v==null?'—':v.toLocaleString('pt-PT',{maximumFractionDigits:1});}

  function ensureStyles(){
    if(document.getElementById(STYLE_ID)) return;
    const link=document.createElement('link');
    link.id=STYLE_ID; link.rel='stylesheet'; link.href='dashboard-portfolio-concentration.css?v=1.4';
    document.head.appendChild(link);
  }

  function segmentMarkup(rows){
    const shown=rows.slice(0,MAX_SEGMENTS);
    const rest=rows.slice(MAX_SEGMENTS).reduce((sum,row)=>sum+row.weight,0);
    const items=[...shown];
    if(rest>0) items.push({label:'Outras',weight:rest,kind:'other'});
    return items.map((row,index)=>`<div class="dpc-segment dpc-segment--${(index%5)+1}" style="flex:${Math.max(row.weight,.04)} 1 0" title="${esc(row.label)} · ${pct(row.weight)}"><span>${esc(row.label)}</span><strong>${pct(row.weight)}</strong></div>`).join('');
  }

  function themeEvidenceMarkup(themes){
    if(!themes?.rows?.length) return '';
    const visible=themes.rows.slice(0,6);
    const buttons=visible.map(row=>`<button type="button" class="dpc-theme-chip${S.selectedTheme===row.label?' is-active':''}" data-dpc-theme="${esc(row.label)}"><span>${esc(row.label)}</span><strong>${pct(row.weight)}</strong></button>`).join('');
    const selected=themes.rows.find(row=>row.label===S.selectedTheme)||null;
    const detail=selected ? `<div class="dpc-theme-detail"><div class="dpc-theme-detail__head"><div><span>COMO SE FORMA</span><strong>${esc(selected.label)} · ${pct(selected.weight)}</strong></div><button type="button" data-dpc-theme-close aria-label="Fechar detalhe">×</button></div><div class="dpc-theme-detail__rows">${selected.contributors.slice(0,5).map(item=>`<div><span>${esc(item.name)}</span><strong>${pct(item.value/themes.total)}</strong></div>`).join('')}</div><small>Contributos calculados sobre o património total. Só entram dados observados; o restante permanece “Não classificado”.</small></div>` : '';
    return `<div class="dpc-theme-evidence"><div class="dpc-theme-evidence__label">TOCA NUM TEMA PARA VER O QUE O COMPÕE</div><div class="dpc-theme-chips">${buttons}</div>${detail}</div>`;
  }

  function metrics(snapshot){
    return `<div class="dpc-metrics">
      <div><span>Maior exposição</span><strong>${pct(snapshot.top1)}</strong></div>
      <div><span>Top 3</span><strong>${pct(snapshot.top3)}</strong></div>
      <div><span>Posições efetivas</span><strong>${effective(snapshot.effective)}</strong><small>1 / HHI</small></div>
    </div>`;
  }

  function modeToggle(hasEtfs){
    return `<div class="dpc-mode" role="group" aria-label="Modo de concentração">
      <button type="button" data-dpc-mode="direct" class="${S.mode==='direct'?'is-active':''}">Direta</button>
      ${hasEtfs?`<button type="button" data-dpc-mode="lookthrough" class="${S.mode==='lookthrough'?'is-active':''}">Look-through ETF</button>`:''}
      <button type="button" data-dpc-mode="themes" class="${S.mode==='themes'?'is-active':''}">Temas</button>
    </div>`;
  }

  function markup(direct){
    if(!direct.count) return `<section class="dpc-card" id="${CARD_ID}"><div class="dpc-head"><div><span class="dpc-kicker">CONCENTRAÇÃO</span><h3>Quanto da carteira é realmente a mesma aposta?</h3></div></div><div class="dpc-empty">Adiciona posições à carteira para calcular a concentração.</div></section>`;

    const fundCount=direct.rows.filter(row=>isFundAsset(row.asset)).length;
    const usingLookthrough=S.mode==='lookthrough'&&fundCount>0;
    const usingThemes=S.mode==='themes';
    const snapshot=usingThemes&&S.themes ? concentrationSnapshot(S.themes.rows) : usingLookthrough&&S.lookthrough ? S.lookthrough : direct;
    const description=usingThemes
      ? 'Cada euro recebe um único tema primário com base em sector, indústria ou descrição observados — nunca apenas pelo nome/ticker; o que não tem evidência suficiente fica explicitamente não classificado.'
      : usingLookthrough
        ? 'Ações diretas e holdings conhecidas dos ETFs são agregadas pela identidade disponível. O restante de cada ETF fica explícito, sem o inventar.'
        : 'Peso das posições individuais. Usa Look-through ETF para revelar sobreposição quando existem holdings verificáveis.';
    const status=usingThemes
      ? S.loading
        ? '<div class="dpc-status">A validar exposição temática…</div>'
        : S.themes
          ? `<div class="dpc-status">Cobertura temática ${pct(S.themes.coverage)} · classificação normalizada a 100%, sem sobreposição entre temas.</div>`
          : '<div class="dpc-status">Ainda sem evidência suficiente para a leitura temática.</div>'
      : usingLookthrough
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
      ${usingThemes?themeEvidenceMarkup(S.themes):''}
      ${status}
      <div class="dpc-foot">${usingThemes ? 'Temas estreitos têm prioridade sobre sectores amplos e cada exposição só entra num tema primário. “Não classificado” preserva a parte sem evidência suficiente.' : usingLookthrough ? 'Sem dupla contagem: cada euro de ETF é repartido pelas holdings conhecidas e por um bloco residual explícito.' : `Cobertura direta: ${snapshot.count} posições · ETFs contam como uma posição única neste modo.`}</div>
    </section>`;
  }

  function mount(){
    const portfolio=document.getElementById('viewAssets');
    if(!portfolio) return null;
    const anchor=document.getElementById('portfolioGlance')||document.getElementById('portfolioSectorCard');
    return {portfolio,anchor};
  }

  function render(){
    ensureStyles();
    const target=mount(); if(!target) return false;
    const shell=document.createElement('div'); shell.innerHTML=markup(concentrationSnapshot());
    const next=shell.firstElementChild; if(!next) return false;
    const existing=document.getElementById(CARD_ID);
    if(existing) existing.replaceWith(next);
    else if(target.anchor) target.anchor.insertAdjacentElement('afterend',next);
    else target.portfolio.appendChild(next);
    return true;
  }

  async function hydrateLookthrough(force=false){
    if(S.loading) return S.lookthrough;
    const assets=(Array.isArray(getState()?.assets)?getState().assets:[]).filter(asset=>assetValue(asset)>0);
    const funds=assets.filter(isFundAsset).filter(asset=>assetTicker(asset));
    if(!funds.length){
      S.lookthrough=null;
      S.themes=buildThemeExposure(assets,{},window.VestraMarketStaticUniverse?.getStocks?.()||[]);
      render();
      return null;
    }
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
      S.details=details;
      S.lookthrough=buildLookthrough(assets,details);
      S.themes=buildThemeExposure(assets,details,window.VestraMarketStaticUniverse?.getStocks?.()||[]);
    }catch(_){
      S.details=details;
      S.lookthrough=buildLookthrough(assets,details);
      S.themes=buildThemeExposure(assets,details,window.VestraMarketStaticUniverse?.getStocks?.()||[]);
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
    window.addEventListener('vestra:app-ready',()=>{S.lookthrough=null;S.themes=null;S.details={};S.selectedTheme='';render();scheduleLookthrough();});
    window.addEventListener('vestra:market-ready',()=>{render();scheduleLookthrough();});
    const net=document.getElementById('kpiNet');
    if(net&&typeof MutationObserver==='function'){
      const observer=new MutationObserver(()=>{S.lookthrough=null;S.themes=null;S.details={};S.selectedTheme='';render();scheduleLookthrough();});
      observer.observe(net,{childList:true,subtree:true,characterData:true});
    }
    document.addEventListener('click',event=>{
      const themeTarget=event.target?.closest?.('[data-dpc-theme]');
      if(themeTarget){
        S.selectedTheme=text(themeTarget.dataset.dpcTheme);
        render();
        return;
      }
      if(event.target?.closest?.('[data-dpc-theme-close]')){
        S.selectedTheme='';
        render();
        return;
      }
      const mode=event.target?.closest?.('[data-dpc-mode]')?.dataset?.dpcMode;
      if(mode==='direct'||mode==='lookthrough'||mode==='themes'){
        S.mode=mode;
        if(mode!=='themes') S.selectedTheme='';
        if(mode==='themes'&&!S.themes){
          const assets=Array.isArray(getState()?.assets)?getState().assets:[];
          S.themes=buildThemeExposure(assets,S.details,window.VestraMarketStaticUniverse?.getStocks?.()||[]);
        }
        render();
        if(mode==='lookthrough'||mode==='themes') void hydrateLookthrough(false);
        return;
      }
      if(event.target?.closest?.('[data-view="assets"]')) setTimeout(()=>{render();scheduleLookthrough();},60);
    });
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot,{once:true}); else boot();

  window.VestraDashboardPortfolioConcentration=Object.freeze({
    version:'1.4',directHoldings,concentrationSnapshot,buildLookthrough,buildThemeExposure,primaryTheme,hydrateLookthrough,render
  });
})();