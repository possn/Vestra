/* Vestra UX v4.52 — compact portfolio, clearer opportunities, politician radar. */
(() => {
  'use strict';
  const VERSION='4.52';
  const t=v=>String(v??'').trim();
  const n=v=>{if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)?x:null;};
  const clamp=v=>Math.max(0,Math.min(100,v));
  const esc=v=>t(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let stocks=[],loading=null;

  function loadStocks(){
    if(loading)return loading;
    loading=fetch(`./data/stocks.json?v=${VERSION}`,{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject()).then(d=>{
      stocks=Array.isArray(d)?d:(Array.isArray(d?.stocks)?d.stocks:[]);return stocks;
    }).catch(()=>[]);
    return loading;
  }

  function priceStats(s){
    const closes=(Array.isArray(s?.price_history_1y)?s.price_history_1y:[]).map(x=>n(x?.close)).filter(x=>x!=null&&x>0);
    const ret=d=>closes.length>d&&closes[closes.length-d-1]>0?(closes.at(-1)/closes[closes.length-d-1]-1)*100:null;
    const hi=closes.length?Math.max(...closes):null,cur=closes.at(-1)||null;
    return {r5:ret(5),r20:ret(20),r60:ret(60),room:hi&&cur?(1-cur/hi)*100:null};
  }
  function timing(s){
    const official=n(s?.opportunity_timing_score); if(official!=null)return official;
    const p=priceStats(s); let x=50;
    if(p.r20!=null)x+=p.r20>=1&&p.r20<=9?22:p.r20>-4&&p.r20<1?8:p.r20>18?-16:p.r20<=-12?-15:0;
    if(p.r60!=null)x+=p.r60>=3&&p.r60<=22?14:p.r60>38?-13:p.r60<=-18?-11:0;
    if(p.r5!=null&&p.r20!=null){if(p.r5>0&&p.r20>=-2&&p.r20<11)x+=5;if(p.r5<-6)x-=6;}
    if(p.room!=null)x+=p.room>=5&&p.room<=26?10:p.room<2?-8:p.room>45?-4:0;
    if(t(s?.estimate_signal)==='improving')x+=8;
    if(t(s?.estimate_signal)==='deteriorating')x-=10;
    if(['confirmed','recovering'].includes(t(s?.recovery_status)))x+=7;
    if(['failed','bounce_only'].includes(t(s?.recovery_status)))x-=10;
    return clamp(x);
  }
  function overextended(s){
    if(typeof s?.opportunity_overextended==='boolean')return s.opportunity_overextended;
    const p=priceStats(s);
    return (p.r20!=null&&p.r20>22)||(p.r60!=null&&p.r60>44)||((p.room!=null&&p.room<2)&&(p.r60!=null&&p.r60>18));
  }
  function eligible(s){
    const qt=t(s?.quote_type||s?.quoteType).toUpperCase();
    if(['ETF','CRYPTOCURRENCY','MUTUALFUND'].includes(qt))return false;
    const sc=n(s?.score),cov=n(s?.data_coverage_pct),conf=n(s?.confidence_score),crit=n(s?.critical_metric_coverage_pct);
    const rel=t(s?.score_reliability).toLowerCase(),risk=t(s?.risk_gate).toLowerCase();
    if(sc==null||sc<58||cov==null||cov<55||conf==null||conf<50)return false;
    if(crit!=null&&crit<35)return false;
    if(['insufficient','suppressed'].includes(rel)||['high','severe'].includes(risk)||t(s?.zombie).toLowerCase()==='yes'||overextended(s))return false;
    return timing(s)>=46;
  }
  function oppScore(s){
    const vals=[
      [n(s?.score),.25],[timing(s),.25],[n(s?.recovery_score),.09],[n(s?.qarp_score),.10],[n(s?.moat_score),.07],
      [n(s?.capital_allocation_intelligence_score),.05],[n(s?.confidence_score),.07],[n(s?.value_pct),.06],[n(s?.growth_pct),.03],[n(s?.sector_native_score),.03]
    ].filter(([v])=>v!=null);
    if(!vals.length)return null;
    let x=vals.reduce((a,[v,w])=>a+clamp(v)*w,0)/vals.reduce((a,[,w])=>a+w,0);
    const fv=n(s?.fair_value_upside_pct),pt=n(s?.analyst_price_target_upside_pct);
    if(fv!=null)x+=Math.max(-7,Math.min(8,fv/4.5)); else if(pt!=null)x+=Math.max(-5,Math.min(6,pt/7));
    const est=t(s?.estimate_signal),rec=t(s?.recovery_status),val=t(s?.valuation_signal),dir=t(s?.thesis_direction);
    if(est==='improving')x+=4;if(est==='deteriorating')x-=7;
    if(['confirmed','recovering'].includes(rec))x+=4;if(['failed','bounce_only'].includes(rec))x-=7;
    if(dir==='up')x+=2;if(dir==='down')x-=3;
    if(val==='overvalued')x-=7;
    if(overextended(s))x=Math.min(x,58);
    return clamp(x);
  }
  function businessBrief(s){
    const d=t(s?.business_summary||s?.longBusinessSummary||s?.long_business_summary||s?.description||s?.company_description);
    if(d)return d;
    const sec=t(s?.sector),ind=t(s?.industry);
    if(sec&&ind&&sec.toLowerCase()!==ind.toLowerCase())return `${ind} · ${sec}`;
    return ind||sec||'Empresa acompanhada pelo Vestra.';
  }
  function opportunityReason(s){
    const p=priceStats(s),bits=[];
    if(t(s?.estimate_signal)==='improving')bits.push('revisões a melhorar');
    if(['confirmed','recovering'].includes(t(s?.recovery_status)))bits.push('recuperação confirmada');
    if(p.r20!=null&&p.r20>=1&&p.r20<=10)bits.push('momentum ainda controlado');
    if(p.room!=null&&p.room>=5&&p.room<=30)bits.push(`${p.room.toFixed(0)}% abaixo do máximo`);
    const fv=n(s?.fair_value_upside_pct),pt=n(s?.analyst_price_target_upside_pct);
    if(fv!=null&&fv>8)bits.push(`upside fundamental +${fv.toFixed(0)}%`);else if(pt!=null&&pt>10)bits.push(`target +${pt.toFixed(0)}%`);
    if(!bits.length)bits.push('qualidade + timing equilibrados');
    return bits.slice(0,3).join(' · ');
  }
  function miniChip(label,value,kind=''){
    if(value===null||value===undefined||value==='')return '';
    return `<span class="ux-opp-chip ${kind}"><b>${esc(label)}</b>${esc(value)}</span>`;
  }
  function oppRow(s){
    const os=oppScore(s),tm=timing(s),p=priceStats(s),fv=n(s?.fair_value_upside_pct),pt=n(s?.analyst_price_target_upside_pct);
    const upside=fv!=null?`${fv>=0?'+':''}${fv.toFixed(0)}%`:pt!=null?`${pt>=0?'+':''}${pt.toFixed(0)}%`:'';
    const momentum=p.r20!=null?`${p.r20>=0?'+':''}${p.r20.toFixed(1)}% / 20d`:'—';
    return `<div class="market-row ux-opp-row" data-market-ticker="${esc(s.ticker)}">
      <div class="ux-opp-main"><div class="market-row__title"><span class="market-row__ticker">${esc(s.ticker)}</span><span class="market-row__name">${esc(s.name||'')}</span></div>
      <div class="market-row__description">${esc(businessBrief(s))}</div>
      <div class="ux-opp-why">✦ ${esc(opportunityReason(s))}</div>
      <div class="ux-opp-chips">${miniChip('Qualidade ',Math.round(n(s?.score)||0))}${miniChip('Timing ',Math.round(tm),'timing')}${miniChip('20d ',momentum,'momentum')}${upside?miniChip('Upside ',upside,'upside'):''}</div></div>
      <div class="ux-opp-score"><small>ENTRY</small><strong>${Math.round(os)}</strong></div></div>`;
  }
  function refineOpportunities(){
    const section=[...document.querySelectorAll('.market-section')].find(x=>t(x.querySelector('h3')?.textContent)==='Melhores oportunidades');
    if(!section||!stocks.length)return;
    const list=section.querySelector('.market-list'); if(!list)return;
    const active=section.querySelector('[data-market-sector].is-active'); const sec=t(active?.dataset.marketSector)||'all';
    let rows=stocks.filter(eligible); if(sec!=='all')rows=rows.filter(s=>t(s?.sector)===sec);
    rows.sort((a,b)=>(oppScore(b)||0)-(oppScore(a)||0)||(timing(b)||0)-(timing(a)||0)); rows=rows.slice(0,12);
    if(!rows.length)return;
    const sig=rows.map(s=>`${t(s.ticker)}:${Math.round(oppScore(s)||0)}`).join('|')+sec;
    if(list.dataset.uxOpp===sig)return;
    list.innerHTML=rows.map(oppRow).join('');list.dataset.uxOpp=sig;
    const h=section.querySelector('.market-section__head h3'); if(h)h.textContent='Oportunidades agora';
    const p=section.querySelector('.market-section__head p'); if(p)p.textContent='Entrada potencial · qualidade + aceleração + recuperação + valuation, sem perseguir preços já esticados';
  }

  const PORTFOLIO_KINDS=[
    {q:'Fila de revisão',kind:'research',icon:'◌',tone:'violet'},
    {q:'Prioridades da carteira',kind:'priority',icon:'✦',tone:'teal'},
    {q:'Mapa da carteira',kind:'map',icon:'◎',tone:'blue'},
    {q:'Candidatos a reforço',kind:'reinforce',icon:'↗',tone:'green'},
    {q:'Posições a rever',kind:'review',icon:'!',tone:'coral'},
    {q:'Concentração e overlap',kind:'overlap',icon:'◉',tone:'amber'},
    {q:'Alternativas no mesmo setor',kind:'swap',icon:'⇄',tone:'purple'},
    {q:'Se substituíres pelo mesmo valor',kind:'scenario',icon:'↔',tone:'purple'},
    {q:'Aderência aos objetivos',kind:'target',icon:'✓',tone:'green'},
    {q:'A carteira está a melhorar?',kind:'history',icon:'↗',tone:'blue'},
    {q:'Diversificação da carteira',kind:'risk',icon:'◇',tone:'coral'},
    {q:'Como reage a carteira?',kind:'stress',icon:'≈',tone:'amber'}
  ];
  function cardTitle(card){return t(card.querySelector('.market-perspective-head h4')?.textContent||card.querySelector(':scope > h4')?.textContent||card.querySelector('h4')?.textContent);}
  function classifyPortfolioCards(){
    const sh=document.getElementById('marketSheet'),c=document.getElementById('marketSheetContent');
    if(!sh||sh.hidden||t(sh.dataset.tool)!=='portfolio'||!c)return;
    c.classList.add('ux-portfolio');
    c.querySelectorAll('.market-detail-card[data-collapsible="1"]').forEach(card=>{
      const title=cardTitle(card);const cfg=PORTFOLIO_KINDS.find(x=>title.includes(x.q)); if(!cfg)return;
      card.dataset.uxKind=cfg.kind;card.dataset.uxTone=cfg.tone;
      let icon=card.querySelector(':scope > .ux-card-icon');
      if(!icon){icon=document.createElement('span');icon.className='ux-card-icon';icon.textContent=cfg.icon;card.appendChild(icon);}
    });
    const toolbar=c.querySelector('.market-collapse-toolbar');
    if(toolbar&&!c.querySelector('.ux-portfolio-shortcuts')){
      const bar=document.createElement('div');bar.className='ux-portfolio-shortcuts';
      bar.innerHTML='<button data-ux-jump="priority">✦ Prioridades</button><button data-ux-jump="swap">⇄ Trocas</button><button data-ux-jump="overlap">◉ Overlap</button><button data-ux-jump="risk">◇ Risco</button>';
      toolbar.insertAdjacentElement('afterend',bar);
    }
    const swap=c.querySelector('[data-ux-kind="swap"]'); if(swap&&!swap.querySelector('.ux-section-hint')){
      const hint=document.createElement('div');hint.className='ux-section-hint';hint.textContent='Trocas inteligentes · compara alternativas sem assumir que vender é obrigatório.';swap.appendChild(hint);
    }
    const overlap=c.querySelector('[data-ux-kind="overlap"]'); if(overlap&&!overlap.querySelector('.ux-section-hint')){
      const hint=document.createElement('div');hint.className='ux-section-hint';hint.textContent='Sobreposição · mostra onde várias posições estão a comprar a mesma exposição.';overlap.appendChild(hint);
    }
  }
  function jumpPortfolio(kind){
    const card=document.querySelector(`#marketSheetContent [data-ux-kind="${kind}"]`);if(!card)return;
    if(card.classList.contains('is-collapsed'))card.querySelector('[data-collapse-toggle]')?.click();
    setTimeout(()=>card.scrollIntoView({behavior:'smooth',block:'start'}),30);
  }

  function enhancePoliticians(){
    const section=document.querySelector('.politicians-section'); if(!section||section.dataset.uxPoliticians==='1')return;
    section.dataset.uxPoliticians='1';
    const picker=section.querySelector('.politician-picker');const sel=picker?.querySelector('[data-politician-select]');if(!picker||!sel)return;
    const search=document.createElement('div');search.className='ux-politician-search';
    search.innerHTML='<span>⌕</span><input type="search" placeholder="Procurar Trump, Pelosi, Tuberville…" autocomplete="off"><div class="ux-politician-matches" hidden></div>';
    picker.prepend(search);
    const input=search.querySelector('input'),matches=search.querySelector('.ux-politician-matches');
    const options=()=>[...sel.options].map(o=>({value:o.value,label:t(o.textContent),group:o.parentElement?.label||''}));
    const show=()=>{
      const q=t(input.value).toLowerCase();if(q.length<2){matches.hidden=true;matches.innerHTML='';return;}
      const found=options().filter(x=>x.label.toLowerCase().includes(q)).slice(0,8);
      matches.innerHTML=found.map(x=>`<button type="button" data-ux-politician-value="${esc(x.value)}"><b>${esc(x.label)}</b><small>${esc(x.group)}</small></button>`).join('')||'<em>Sem correspondências.</em>';matches.hidden=false;
    };
    input.addEventListener('input',show);
    search.addEventListener('click',e=>{
      const b=e.target.closest('[data-ux-politician-value]');if(!b)return;
      sel.value=b.dataset.uxPoliticianValue;sel.dispatchEvent(new Event('change',{bubbles:true}));input.value=t(b.querySelector('b')?.textContent).split(' · ')[0];matches.hidden=true;
    });
    const controls=document.createElement('div');controls.className='ux-politician-controls';
    controls.innerHTML='<button class="is-active" data-ux-politician-view="all">Tudo</button><button data-ux-politician-view="buy">↗ Compras</button><button data-ux-politician-view="sell">↘ Vendas</button><button data-ux-politician-fav>☆ Favorito</button>';
    picker.insertAdjacentElement('afterend',controls);
    const key='vestra-politician-favourites-v1';
    function currentName(){return t(document.querySelector('#politicianProfile h3')?.textContent||sel.selectedOptions?.[0]?.textContent).split(' · ')[0];}
    function favs(){try{return new Set(JSON.parse(localStorage.getItem(key)||'[]'))}catch{return new Set()}}
    function updateFav(){const b=controls.querySelector('[data-ux-politician-fav]'),f=favs(),name=currentName();if(!b)return;b.textContent=f.has(name)?'★ Favorito':'☆ Favorito';b.classList.toggle('is-fav',f.has(name));}
    controls.addEventListener('click',e=>{
      const view=e.target.closest('[data-ux-politician-view]');
      if(view){controls.querySelectorAll('[data-ux-politician-view]').forEach(x=>x.classList.toggle('is-active',x===view));section.dataset.uxPoliticianView=view.dataset.uxPoliticianView;applyPoliticianView(section);return;}
      const fav=e.target.closest('[data-ux-politician-fav]');if(fav){const f=favs(),name=currentName();f.has(name)?f.delete(name):f.add(name);try{localStorage.setItem(key,JSON.stringify([...f]))}catch{}updateFav();}
    });
    updateFav();
    setTimeout(()=>{addPoliticianPulse(section);updateFav();},50);
  }
  function applyPoliticianView(section){
    const view=t(section.dataset.uxPoliticianView||'all');
    section.querySelectorAll('.politician-sides > section').forEach((x,i)=>x.style.display=view==='all'||(view==='buy'&&i===0)||(view==='sell'&&i===1)?'':'none');
    section.querySelectorAll('.politician-trade').forEach(x=>{
      const em=x.querySelector('em');const buy=em?.classList.contains('is-buy'),sell=em?.classList.contains('is-sell');x.style.display=view==='all'||(view==='buy'&&buy)||(view==='sell'&&sell)?'':'none';
    });
  }
  function addPoliticianPulse(section){
    const profile=section.querySelector('.politician-profile');if(!profile||profile.querySelector('.ux-politician-pulse'))return;
    const kpis=[...profile.querySelectorAll('.politician-kpis span')];
    let buys=0,sells=0;kpis.forEach(k=>{const label=t(k.querySelector('small')?.textContent).toLowerCase(),val=parseInt(t(k.querySelector('strong')?.textContent).replace(/[^0-9]/g,''),10)||0;if(label.includes('compra'))buys=val;if(label.includes('venda'))sells=val;});
    const pulse=document.createElement('div');pulse.className='ux-politician-pulse '+(buys>sells?'is-buy':sells>buys?'is-sell':'');
    pulse.innerHTML=`<span>${buys>sells?'↗':sells>buys?'↘':'↔'}</span><div><small>RADAR</small><strong>${buys>sells?'Mais comprador':sells>buys?'Mais vendedor':'Equilibrado'}</strong><em>${buys} compras · ${sells} vendas no período carregado</em></div>`;
    profile.appendChild(pulse);
  }

  function addStyle(){
    if(document.getElementById('vestra-ux-v452-style'))return;
    const s=document.createElement('style');s.id='vestra-ux-v452-style';s.textContent=`
      .ux-portfolio .market-collapse-toolbar{background:linear-gradient(135deg,rgba(23,123,120,.09),rgba(89,113,190,.06));border:0;padding:9px 10px;position:sticky;top:0;z-index:5;backdrop-filter:blur(10px)}
      .ux-portfolio .market-detail-card[data-collapsible="1"].is-collapsed{min-height:74px;padding:13px 52px 12px 50px!important;border-left:4px solid rgba(23,123,120,.25);box-shadow:0 3px 12px rgba(19,41,52,.035)}
      .ux-portfolio .market-detail-card[data-collapsible="1"].is-collapsed .market-perspective-head{min-height:44px;align-items:center}.ux-portfolio .market-detail-card[data-collapsible="1"].is-collapsed .market-perspective-head small{font-size:9px;letter-spacing:.13em}.ux-portfolio .market-detail-card[data-collapsible="1"].is-collapsed h4{font-size:16px;line-height:1.15}
      .ux-card-icon{position:absolute;left:14px;top:50%;transform:translateY(-50%);width:27px;height:27px;border-radius:9px;display:grid;place-items:center;background:rgba(23,123,120,.08);font-weight:900;color:#177b78}.market-detail-card:not(.is-collapsed)>.ux-card-icon{display:none}
      [data-ux-tone="violet"].is-collapsed{border-left-color:#8c78c5!important}[data-ux-tone="violet"] .ux-card-icon{color:#705bb0;background:#f1edfb}
      [data-ux-tone="teal"].is-collapsed{border-left-color:#1e9a95!important}[data-ux-tone="blue"].is-collapsed{border-left-color:#5b86c4!important}[data-ux-tone="green"].is-collapsed{border-left-color:#49a878!important}[data-ux-tone="coral"].is-collapsed{border-left-color:#da806f!important}[data-ux-tone="amber"].is-collapsed{border-left-color:#d6a34a!important}[data-ux-tone="purple"].is-collapsed{border-left-color:#9a78c9!important}
      .ux-portfolio-shortcuts{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin:0 0 12px}.ux-portfolio-shortcuts button{border:0;border-radius:13px;padding:10px 5px;background:linear-gradient(145deg,var(--card),var(--soft));color:var(--text);font-size:10px;font-weight:800;box-shadow:0 3px 12px rgba(19,41,52,.05)}
      .ux-section-hint{font-size:11px;color:var(--text2);padding:8px 0 2px}.is-collapsed>.ux-section-hint{display:none!important}
      [data-ux-kind="swap"]:not(.is-collapsed),[data-ux-kind="scenario"]:not(.is-collapsed){background:linear-gradient(145deg,var(--card),rgba(143,112,199,.06))}[data-ux-kind="overlap"]:not(.is-collapsed){background:linear-gradient(145deg,var(--card),rgba(216,163,74,.07))}
      .ux-opp-row{align-items:center!important;padding:13px!important;border:1px solid var(--line);border-radius:18px!important;background:linear-gradient(135deg,var(--card),rgba(23,123,120,.045));margin-bottom:9px}.ux-opp-main{min-width:0;flex:1}.ux-opp-why{font-size:10.5px;color:#177b78;font-weight:700;margin-top:5px}.ux-opp-chips{display:flex;gap:5px;flex-wrap:wrap;margin-top:7px}.ux-opp-chip{font-size:9px;padding:4px 7px;border-radius:999px;background:var(--soft);color:var(--text2)}.ux-opp-chip b{color:var(--text);font-weight:800}.ux-opp-chip.timing{background:rgba(23,123,120,.09)}.ux-opp-chip.upside{background:rgba(73,168,120,.11)}.ux-opp-score{width:58px;height:62px;border-radius:17px;background:linear-gradient(145deg,#dff3ef,#caebe6);display:grid;place-items:center;align-content:center;color:#126d69;flex:0 0 auto}.ux-opp-score small{font-size:8px;font-weight:900;letter-spacing:.12em}.ux-opp-score strong{font-size:22px;line-height:1}
      .ux-politician-search{position:relative;display:grid;grid-template-columns:20px 1fr;align-items:center;gap:5px;border:1px solid var(--line);border-radius:14px;background:var(--card);padding:9px 11px;margin-bottom:9px}.ux-politician-search input{border:0!important;background:transparent!important;outline:0;width:100%;font:inherit;color:var(--text)}.ux-politician-matches{position:absolute;left:0;right:0;top:calc(100% + 5px);z-index:20;background:var(--card);border:1px solid var(--line);border-radius:15px;padding:6px;box-shadow:0 15px 35px rgba(20,37,45,.16);max-height:280px;overflow:auto}.ux-politician-matches button{display:grid;width:100%;text-align:left;border:0;background:none;padding:9px;border-radius:10px;color:var(--text)}.ux-politician-matches button:active{background:var(--soft)}.ux-politician-matches small{color:var(--text2)}.ux-politician-matches em{padding:10px;color:var(--text2)}
      .ux-politician-controls{display:flex;gap:7px;overflow:auto;margin:-7px 0 12px;padding-bottom:2px}.ux-politician-controls button{white-space:nowrap;border:1px solid var(--line);border-radius:999px;background:var(--card);padding:7px 10px;color:var(--text2);font-size:10px;font-weight:800}.ux-politician-controls button.is-active{background:#165f6c;color:white;border-color:#165f6c}.ux-politician-controls button.is-fav{color:#b27a16;background:#fff8df}
      .ux-politician-pulse{grid-column:1/-1;display:flex;gap:10px;align-items:center;padding:11px 12px;border-radius:14px;background:var(--soft);margin-top:3px}.ux-politician-pulse>span{font-size:22px}.ux-politician-pulse div{display:grid}.ux-politician-pulse small{font-size:8px;font-weight:900;letter-spacing:.12em;color:var(--text2)}.ux-politician-pulse strong{font-size:13px}.ux-politician-pulse em{font-size:10px;font-style:normal;color:var(--text2)}.ux-politician-pulse.is-buy{background:rgba(33,178,143,.08)}.ux-politician-pulse.is-sell{background:rgba(217,93,114,.08)}
      @media(max-width:420px){.ux-portfolio-shortcuts{grid-template-columns:repeat(2,1fr)}.ux-portfolio .market-detail-card[data-collapsible="1"].is-collapsed{min-height:68px}.ux-opp-chip{font-size:8.5px}.ux-opp-score{width:52px;height:57px}.ux-opp-score strong{font-size:20px}}
    `;document.head.appendChild(s);
  }

  document.addEventListener('click',e=>{const b=e.target.closest?.('[data-ux-jump]');if(b){e.preventDefault();e.stopPropagation();jumpPortfolio(b.dataset.uxJump);}});

  function apply(){refineOpportunities();classifyPortfolioCards();enhancePoliticians();const p=document.querySelector('.politicians-section');if(p){applyPoliticianView(p);addPoliticianPulse(p);}}
  function start(){addStyle();loadStocks().then(()=>{apply();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});});mo.observe(document.body,{childList:true,subtree:true});});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
