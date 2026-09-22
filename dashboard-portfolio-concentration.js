/* Vestra Portfolio Concentration v1.7 — clearer concentration + broader thematic evidence. */
(() => {
  'use strict';

  const CARD_ID='dashboardPortfolioConcentrationCard';
  const THEME_CARD_ID='portfolioThemeExposureCard';
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

  function portfolioShowsAssets(){
    const assetsTab=document.getElementById('segAssets');
    return !assetsTab || assetsTab.classList.contains('seg__btn--active');
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
    ['Semicondutores', s => /semiconductor|chip|microprocessor|integrated circuit|foundry/i.test(s.text)],
    ['IA & Robótica', s => /artificial intelligence|machine learning|robotics|robotic|automation|generative ai|neural network|accelerated computing/i.test(s.text)],
    ['Cloud & Data Centers', s => /data center|datacenter|cloud computing|cloud infrastructure|hyperscale|hyperscaler|server infrastructure/i.test(s.text)],
    ['Cibersegurança', s => /cybersecurity|cyber security|information security|network security/i.test(s.text)],
    ['Biotecnologia', s => /biotech|biotechnology|biopharma|biopharmaceutical/i.test(s.text)],
    ['Defesa & Aeroespacial', s => /aerospace|defen[cs]e|military/i.test(s.text)],
    ['Energia limpa', s => /renewable|solar|wind energy|clean energy|hydrogen|fuel cell/i.test(s.text)],
    ['Nuclear & Urânio', s => /nuclear|uranium/i.test(s.text)],
    ['Água', s => /water|wastewater|desalination/i.test(s.text)],
    ['Agricultura', s => /agricultur|farm|fertili[sz]er|crop|seed|grain/i.test(s.text)],
    ['Matérias-primas', s => /mining|metals?|commodit|copper|gold|silver|lithium|steel|basic materials|materiais/i.test(s.text)||s.sector==='Basic Materials'||s.sector==='Materiais'],
    ['Imobiliário', s => /reit|real estate|imobili/i.test(s.text)||s.sector==='Real Estate'||s.sector==='Imobiliário'],
    ['Tecnologia', s => /technology|tecnologia/i.test(s.sector)],
    ['Saúde', s => /healthcare|health care|saúde|saude/i.test(s.sector)],
    ['Financeiro', s => /financial|financeiro|financeiros|bancos/i.test(s.sector)],
    ['Indústria', s => /industrial|industriais|indústria|industria/i.test(s.sector)],
    ['Energia', s => /^energy$|^energia$/i.test(s.sector)],
    ['Consumo', s => /consumer|consumo/i.test(s.sector)],
    ['Utilities', s => /utilities|utilidades/i.test(s.sector)],
    ['Comunicações', s => /communication|comunica/i.test(s.sector)],
  ];

  function themeEvidence(row){
    if(!row) return null;
    const sector=text(row?.sector);
    const blob=[
      row?.sector,row?.industry,row?.category,row?.theme,row?.stock_theme,row?.style,
      row?.description,row?.long_business_summary,row?.business_summary,
      row?.meta?.industry,row?.meta?.category,row?.meta?.fundFamily,row?.meta?.sector
    ].map(text).join(' ');
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

  function isThemeEligibleAsset(asset){
    if(!(assetValue(asset)>0)) return false;
    if(typeof window.isPortfolioEquityAsset==='function'){
      try{ if(window.isPortfolioEquityAsset(asset)) return true; }catch(_){}
    }
    const quoteType=text(asset?.meta?.quoteType||asset?.meta?.quote_type).toUpperCase();
    if(quoteType==='EQUITY'||quoteType==='ETF') return true;
    const cls=text(asset?.class).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
    if(/acao|acoes|etf/.test(cls)) return true;
    return isFundAsset(asset)&&Boolean(assetTicker(asset));
  }

  function assetThemeEvidence(asset,ticker,detailsByTicker,byTicker){
    const detail=detailsByTicker[ticker]||byTicker.get(ticker)||null;
    if(detail) return detail;
    const meta=asset?.meta||{};
    let sector=text(meta.sector);
    if(!sector&&typeof window.portfolioEquitySector==='function'){
      try{
        const resolved=text(window.portfolioEquitySector(asset));
        if(resolved&&resolved!=='Sector por identificar'&&resolved!=='ETF diversificado') sector=resolved;
      }catch(_){}
    }
    if(!sector&&typeof window.getTickerMeta==='function'){
      try{ sector=text(window.getTickerMeta(asset)?.sector); }catch(_){}
    }
    return {
      sector,
      industry:meta.industry,
      category:meta.category,
      fundFamily:meta.fundFamily,
      description:asset?.description||meta.description,
      name:asset?.name,
    };
  }

  function buildThemeExposure(assets,detailsByTicker={},stocks=[]){
    const rows=Array.isArray(assets)?assets:[];
    const portfolioTotal=rows.reduce((sum,asset)=>sum+(assetValue(asset)||0),0);
    const eligible=rows.filter(isThemeEligibleAsset);
    const marketTotal=eligible.reduce((sum,asset)=>sum+(assetValue(asset)||0),0);
    if(!(portfolioTotal>0)||!(marketTotal>0)) return {
      total:portfolioTotal,marketTotal,marketShare:portfolioTotal>0?marketTotal/portfolioTotal:null,
      coverage:null,rows:[],classifiedValue:0
    };

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

    eligible.forEach((asset,assetIndex)=>{
      const value=assetValue(asset);
      const ticker=assetTicker(asset);
      if(!isFundAsset(asset)){
        const evidence=resolve(ticker,assetThemeEvidence(asset,ticker,detailsByTicker,byTicker));
        add(primaryTheme(evidence),value,ticker||text(asset?.name)||`Posição ${assetIndex+1}`);
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

      if(!valid){
        const fallbackTheme=primaryTheme(assetThemeEvidence(asset,ticker,detailsByTicker,byTicker));
        add(fallbackTheme,value,ticker||text(asset?.name)||'ETF/Fundo');
        return;
      }

      const scale=rawCoverage>1?1/rawCoverage:1;
      let allocated=0;
      for(const holding of parsed){
        const contribution=value*holding.fraction*scale;
        allocated+=contribution;
        add(holding.theme,contribution,`${ticker||text(asset?.name)||'ETF'} → ${holding.label}`);
      }
      const residual=Math.max(0,value-allocated);
      if(residual>.01){
        const residualTheme=primaryTheme(assetThemeEvidence(asset,ticker,detailsByTicker,byTicker));
        add(residualTheme,residual,`${ticker||text(asset?.name)||'ETF'} → restante`);
      }
    });

    const themeRows=[...buckets.entries()].map(([label,bucket])=>({
      label,
      value:bucket.value,
      weight:bucket.value/portfolioTotal,
      marketWeight:bucket.value/marketTotal,
      kind:label==='Não classificado'?'unclassified':'theme',
      contributors:[...bucket.contributors.entries()].map(([name,value])=>({
        name,value,weight:value/portfolioTotal,marketWeight:value/marketTotal
      })).sort((a,b)=>b.value-a.value),
    })).sort((a,b)=>b.value-a.value);

    return {
      total:portfolioTotal,
      marketTotal,
      marketShare:marketTotal/portfolioTotal,
      coverage:classifiedValue/marketTotal,
      rows:themeRows,
      classifiedValue
    };
  }

  function pct(v){return v==null?'—':`${(v*100).toLocaleString('pt-PT',{maximumFractionDigits:1})}%`;}
  function effective(v){return v==null?'—':v.toLocaleString('pt-PT',{maximumFractionDigits:1});}

  function ensureStyles(){
    if(document.getElementById(STYLE_ID)) return;
    const link=document.createElement('link');
    link.id=STYLE_ID; link.rel='stylesheet'; link.href='dashboard-portfolio-concentration.css?v=1.7';
    document.head.appendChild(link);
  }

  function segmentMarkup(rows){
    const shown=rows.slice(0,MAX_SEGMENTS);
    const rest=rows.slice(MAX_SEGMENTS).reduce((sum,row)=>sum+row.weight,0);
    const items=[...shown];
    if(rest>0) items.push({label:'Outras',weight:rest,kind:'other'});
    return items.map((row,index)=>`<div class="dpc-segment dpc-segment--${(index%5)+1}" style="flex:${Math.max(row.weight,.04)} 1 0" title="${esc(row.label)} · ${pct(row.weight)}"><span>${esc(row.label)}</span><strong>${pct(row.weight)}</strong></div>`).join('');
  }

  function themeRowsForDisplay(themes){
    const rows=Array.isArray(themes?.rows)?themes.rows:[];
    const classified=rows.filter(row=>row.kind==='theme');
    const unknown=rows.find(row=>row.kind==='unclassified')||null;
    const visible=classified.slice(0,8);
    if(unknown?.marketWeight>0.001) visible.push(unknown);
    return {classified,unknown,visible};
  }

  function themeEvidenceMarkup(themes){
    if(!themes?.rows?.length) return '';
    const {visible}=themeRowsForDisplay(themes);
    const buttons=visible.map(row=>`<button type="button" class="dpc-theme-chip${S.selectedTheme===row.label?' is-active':''}" data-dpc-theme="${esc(row.label)}"><span>${esc(row.label)}</span><strong>${pct(row.weight)}</strong></button>`).join('');
    const selected=themes.rows.find(row=>row.label===S.selectedTheme)||null;
    const detail=selected ? `<div class="dpc-theme-detail"><div class="dpc-theme-detail__head"><div><span>COMO SE FORMA</span><strong>${esc(selected.label)} · ${pct(selected.weight)} do património</strong></div><button type="button" data-dpc-theme-close aria-label="Fechar detalhe">×</button></div><div class="dpc-theme-detail__rows">${selected.contributors.slice(0,6).map(item=>`<div><span>${esc(item.name)}</span><strong>${pct(item.weight)}</strong></div>`).join('')}</div><small>${pct(selected.marketWeight)} da fatia de mercado. Inclui posições diretas e holdings de ETFs quando existem dados verificáveis.</small></div>` : '';
    return `<div class="dpc-theme-evidence"><div class="dpc-theme-evidence__label">VER O QUE COMPÕE CADA TEMA</div><div class="dpc-theme-chips">${buttons}</div>${detail}</div>`;
  }

  function themeExposureMarkup(themes){
    if(!(themes?.marketTotal>0)) return '';
    const {classified,unknown,visible}=themeRowsForDisplay(themes);
    const largest=classified[0]||null;
    const segments=visible.map((row,index)=>`<span class="dpc-theme-bar__segment dpc-segment--${(index%5)+1}" style="width:${Math.max(row.marketWeight*100,2)}%" title="${esc(row.label)} · ${pct(row.weight)} do património"></span>`).join('');
    const list=classified.slice(0,8).map(row=>`<button type="button" data-dpc-theme="${esc(row.label)}"><span>${esc(row.label)}<small>${pct(row.marketWeight)} dos ativos de mercado</small></span><strong>${pct(row.weight)}</strong></button>`).join('');
    const unknownMarket=unknown?.marketWeight||0;
    const answer=largest
      ? `A maior exposição temática identificada é <b>${esc(largest.label)}</b>: ${pct(largest.weight)} do património total.`
      : 'Ainda não há evidência suficiente para identificar temas nesta fatia da carteira.';
    return `<section class="dpc-card dpc-theme-card" id="${THEME_CARD_ID}">
      <div class="dpc-head"><div><span class="dpc-kicker">EXPOSIÇÃO TEMÁTICA</span><h3>Onde estão as tuas apostas de mercado?</h3><p>Analisa apenas ações, ETFs e fundos com ticker. Depósitos, obrigações, PPR, imóveis e cripto não baixam artificialmente a cobertura temática.</p></div></div>
      <div class="dpc-answer dpc-answer--theme">${answer}</div>
      <div class="dpc-theme-stats">
        <div><span>Ativos de mercado</span><strong>${pct(themes.marketShare)}</strong><small>do património total</small></div>
        <div><span>Maior tema</span><strong>${largest?esc(largest.label):'—'}</strong><small>${largest?pct(largest.weight)+' do património':'sem evidência'}</small></div>
        <div><span>Cobertura temática</span><strong>${pct(themes.coverage)}</strong><small>${unknownMarket>0.001?`${pct(unknownMarket)} da fatia de mercado por classificar`:'fatia de mercado classificada'}</small></div>
      </div>
      <div class="dpc-theme-bar-label"><span>Composição dos ativos de mercado</span><small>100% = ações + ETFs + fundos analisáveis</small></div>
      <div class="dpc-theme-bar" aria-label="Composição temática dos ativos de mercado">${segments}</div>
      <div class="dpc-theme-list">${list||'<div class="dpc-empty">Ainda sem temas classificados.</div>'}</div>
      ${themeEvidenceMarkup(themes)}
      <div class="dpc-foot">Percentagens grandes = peso no património total. O detalhe mostra também o peso dentro da fatia de mercado. Temas estreitos têm prioridade sobre sectores amplos e não há dupla contagem.</div>
    </section>`;
  }

  function metrics(snapshot,usingLookthrough=false){
    return `<div class="dpc-metrics">
      <div><span>${usingLookthrough?'Maior exposição':'Maior posição'}</span><strong>${pct(snapshot.top1)}</strong></div>
      <div><span>${usingLookthrough?'Top 3 exposições':'Top 3 posições'}</span><strong>${pct(snapshot.top3)}</strong></div>
      <div><span>Equivalente a</span><strong>${effective(snapshot.effective)}</strong><small>posições iguais · índice HHI</small></div>
    </div>`;
  }

  function modeToggle(hasEtfs){
    if(!hasEtfs) return '';
    return `<div class="dpc-mode" role="group" aria-label="Modo de concentração">
      <button type="button" data-dpc-mode="direct" class="${S.mode==='direct'?'is-active':''}">Posições</button>
      <button type="button" data-dpc-mode="lookthrough" class="${S.mode==='lookthrough'?'is-active':''}">Dentro dos ETFs</button>
    </div>`;
  }

  function markup(direct){
    if(!direct.count) return `<section class="dpc-card" id="${CARD_ID}"><div class="dpc-head"><div><span class="dpc-kicker">CONCENTRAÇÃO</span><h3>Concentração das posições</h3></div></div><div class="dpc-empty">Adiciona posições à carteira para calcular a concentração.</div></section>`;

    const fundCount=direct.rows.filter(row=>isFundAsset(row.asset)).length;
    const usingLookthrough=S.mode==='lookthrough'&&fundCount>0;
    const snapshot=usingLookthrough&&S.lookthrough ? S.lookthrough : direct;
    const top3Text=pct(snapshot.top3);
    const answer=usingLookthrough
      ? `Depois de abrir os ETFs, as 3 maiores exposições representam <b>${top3Text}</b> do património.`
      : `As 3 maiores posições representam <b>${top3Text}</b> do património.`;
    const description=usingLookthrough
      ? 'Vê as empresas que estão por baixo dos ETFs e soma exposições repetidas sem dupla contagem.'
      : 'Mede concentração por posição. Este modo não assume que duas posições diferentes são a mesma aposta.';

    const status=usingLookthrough
      ? S.loading
        ? '<div class="dpc-status">A abrir as holdings dos ETFs…</div>'
        : S.lookthrough
          ? `<div class="dpc-status">Holdings disponíveis em ${pct(S.lookthrough.etfCoverage)} dos ETFs · ${pct(S.lookthrough.knownUnderlyingWeight)} do património identificado por baixo dos ETFs.</div>`
          : '<div class="dpc-status">Ainda sem holdings suficientes para abrir os ETFs.</div>'
      : '';

    return `<section class="dpc-card" id="${CARD_ID}">
      <div class="dpc-head"><div><span class="dpc-kicker">CONCENTRAÇÃO</span><h3>Concentração das posições</h3><p>${description}</p></div></div>
      <div class="dpc-answer">${answer}</div>
      ${modeToggle(fundCount>0)}
      ${metrics(snapshot,usingLookthrough)}
      <div class="dpc-mosaic" aria-label="Peso das maiores posições">${segmentMarkup(snapshot.rows)}</div>
      ${status}
      <div class="dpc-foot">${usingLookthrough ? 'Dentro dos ETFs, cada euro é repartido pelas holdings conhecidas e por um residual explícito.' : `${snapshot.count} posições com valor · ETFs contam como uma posição neste modo.`}</div>
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
    if(!portfolioShowsAssets()){
      document.getElementById(CARD_ID)?.remove();
      document.getElementById(THEME_CARD_ID)?.remove();
      return true;
    }

    const assets=(Array.isArray(getState()?.assets)?getState().assets:[]).filter(asset=>assetValue(asset)>0);
    S.themes=buildThemeExposure(assets,S.details,window.VestraMarketStaticUniverse?.getStocks?.()||[]);

    const shell=document.createElement('div'); shell.innerHTML=markup(concentrationSnapshot());
    const next=shell.firstElementChild; if(!next) return false;
    const existing=document.getElementById(CARD_ID);
    if(existing) existing.replaceWith(next);
    else if(target.anchor) target.anchor.insertAdjacentElement('afterend',next);
    else target.portfolio.appendChild(next);

    const themeShell=document.createElement('div'); themeShell.innerHTML=themeExposureMarkup(S.themes);
    const themeNext=themeShell.firstElementChild;
    const themeExisting=document.getElementById(THEME_CARD_ID);
    if(themeNext){
      if(themeExisting) themeExisting.replaceWith(themeNext);
      else document.getElementById(CARD_ID)?.insertAdjacentElement('afterend',themeNext);
    }else themeExisting?.remove();
    return true;
  }

  function hydrationCandidates(assets){
    const funds=assets.filter(asset=>isFundAsset(asset)&&assetTicker(asset)).sort((a,b)=>assetValue(b)-assetValue(a)).slice(0,18);
    const direct=assets.filter(asset=>!isFundAsset(asset)&&isThemeEligibleAsset(asset)&&assetTicker(asset)).sort((a,b)=>assetValue(b)-assetValue(a)).slice(0,24);
    const seen=new Set();
    return [...funds,...direct].filter(asset=>{
      const ticker=assetTicker(asset);
      if(!ticker||seen.has(ticker)) return false;
      seen.add(ticker); return true;
    }).slice(0,36);
  }

  async function hydrateLookthrough(force=false){
    if(S.loading) return S.lookthrough;
    const assets=(Array.isArray(getState()?.assets)?getState().assets:[]).filter(asset=>assetValue(asset)>0);
    const candidates=hydrationCandidates(assets);
    const funds=assets.filter(isFundAsset).filter(asset=>assetTicker(asset));
    if(!candidates.length){
      S.lookthrough=funds.length?buildLookthrough(assets,{}):null;
      S.themes=buildThemeExposure(assets,{},window.VestraMarketStaticUniverse?.getStocks?.()||[]);
      render();
      return S.lookthrough;
    }
    if(Object.keys(S.details).length&&!force){render();return S.lookthrough;}
    S.loading=true;render();
    const details={...S.details};
    try{
      await window.VestraMarketLoader?.ensureHelpers?.();
      const hydrate=window.VestraMarketData?.hydrateTicker;
      if(typeof hydrate==='function'){
        for(let i=0;i<candidates.length;i+=6){
          const batch=candidates.slice(i,i+6);
          const settled=await Promise.allSettled(batch.map(asset=>hydrate(assetTicker(asset))));
          settled.forEach((row,index)=>{if(row.status==='fulfilled'&&row.value)details[assetTicker(batch[index])]=row.value;});
        }
      }
      S.details=details;
      S.lookthrough=funds.length?buildLookthrough(assets,details):null;
      S.themes=buildThemeExposure(assets,details,window.VestraMarketStaticUniverse?.getStocks?.()||[]);
    }catch(_){
      S.details=details;
      S.lookthrough=funds.length?buildLookthrough(assets,details):null;
      S.themes=buildThemeExposure(assets,details,window.VestraMarketStaticUniverse?.getStocks?.()||[]);
    }finally{
      S.loading=false;render();
    }
    return S.lookthrough;
  }

  function scheduleLookthrough(){
    if(S.scheduled) return;
    const assets=Array.isArray(getState()?.assets)?getState().assets:[];
    if(!assets.some(asset=>isThemeEligibleAsset(asset)&&assetTicker(asset))) return;
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
      if(mode==='direct'||mode==='lookthrough'){
        S.mode=mode;
        S.selectedTheme='';
        render();
        if(mode==='lookthrough') void hydrateLookthrough(false);
        return;
      }
      if(event.target?.closest?.('[data-view="assets"],#segAssets,#segLiabs')) setTimeout(()=>{render();scheduleLookthrough();},60);
    });
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot,{once:true}); else boot();

  window.VestraDashboardPortfolioConcentration=Object.freeze({
    version:'1.7',directHoldings,concentrationSnapshot,buildLookthrough,buildThemeExposure,primaryTheme,hydrateLookthrough,render
  });
})();