/* Vestra Swap Lab v1.0 — canonical portfolio swap comparator. */
(() => {
  'use strict';
  const t=v=>String(v??'').trim();
  const n=v=>{if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)?x:null;};
  const esc=v=>t(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  function stocks(){
    const rows=window.VestraMarketStaticUniverse?.getStocks?.();
    return Array.isArray(rows)?rows:[];
  }
  function stock(ticker){
    const tk=t(ticker).toUpperCase(); if(!tk)return null;
    const universe=stocks();
    return universe.find(s=>t(s?.ticker).toUpperCase()===tk)||universe.find(s=>t(s?.ticker).toUpperCase().split('.')[0]===tk.split('.')[0])||null;
  }
  function pct(v){const x=n(v);return x==null?'—':`${(Math.abs(x)<=1?x*100:x).toFixed(1)}%`;}
  function multiple(v){const x=n(v);return x==null||x<=0?'—':x.toFixed(1);}
  function score(v){const x=n(v);return x==null?'—':Math.round(x);}
  function priceStats(s){
    const c=(Array.isArray(s?.price_history_1y)?s.price_history_1y:[]).map(x=>n(x?.close)).filter(x=>x>0);
    const ret=d=>c.length>d?(c.at(-1)/c[c.length-d-1]-1)*100:null;
    const hi=c.length?Math.max(...c):null,cur=c.at(-1)||null;
    return {r20:ret(20),r60:ret(60),room:hi&&cur?(1-cur/hi)*100:null};
  }
  function timing(s){
    const official=n(s?.opportunity_timing_score); if(official!=null)return official;
    const p=priceStats(s);let x=50;
    if(p.r20!=null)x+=p.r20>=0&&p.r20<=10?18:p.r20>20?-15:p.r20<-10?-12:0;
    if(p.r60!=null)x+=p.r60>=2&&p.r60<=25?12:p.r60>40?-12:p.r60<-18?-10:0;
    if(p.room!=null)x+=p.room>=5&&p.room<=30?10:p.room<2?-8:0;
    if(t(s?.estimate_signal)==='improving')x+=7;
    if(['confirmed','recovering'].includes(t(s?.recovery_status)))x+=6;
    return Math.max(0,Math.min(100,x));
  }
  function metric(label,a,b,fmt=x=>score(x),higher=true){
    const av=n(a),bv=n(b); let cls='';
    if(av!=null&&bv!=null){const better=higher?bv>av:bv<av;const worse=higher?bv<av:bv>av;cls=better?'is-better':worse?'is-worse':'';}
    return `<div class="ux456-metric"><span>${esc(label)}</span><b>${esc(fmt(a))}</b><i>→</i><strong class="${cls}">${esc(fmt(b))}</strong></div>`;
  }
  function parseCandidate(row){
    const target=t(row.dataset.marketTicker); if(!target)return null;
    const text=t(row.textContent);
    const m=text.match(/Alternativa\s+a\s+([A-Z0-9.\-]+)/i);
    const source=m?t(m[1]):'';
    return {source,target,row};
  }
  function candidates(card){
    const seen=new Set(),out=[];
    card.querySelectorAll('[data-market-ticker]').forEach(row=>{
      const c=parseCandidate(row);if(!c||!c.source||!c.target)return;
      const key=`${c.source}->${c.target}`;if(seen.has(key))return;seen.add(key);out.push(c);
    });
    return out;
  }
  function verdict(a,b){
    let wins=0,losses=0,reasons=[];
    const cmp=(label,av,bv,higher=true,threshold=0)=>{if(av==null||bv==null)return;const d=higher?bv-av:av-bv;if(d>threshold){wins++;reasons.push(`${label} melhora`);}else if(d<-threshold)losses++;};
    cmp('qualidade',n(a?.score),n(b?.score),true,3);
    cmp('timing',timing(a),timing(b),true,5);
    cmp('confiança',n(a?.confidence_score),n(b?.confidence_score),true,5);
    cmp('ROE',n(a?.roe),n(b?.roe),true,0.02);
    cmp('FCF yield',n(a?.free_cash_flow_yield_pct),n(b?.free_cash_flow_yield_pct),true,1);
    cmp('Forward P/E',n(a?.forward_pe),n(b?.forward_pe),false,2);
    if(wins>=3&&losses<=1)return {tone:'good',title:'Troca potencialmente favorável',text:reasons.slice(0,3).join(' · ')};
    if(losses>=3)return {tone:'bad',title:'Não melhora claramente a carteira',text:'A alternativa perde em demasiadas dimensões relevantes.'};
    return {tone:'neutral',title:'Troca inconclusiva',text:reasons.length?reasons.slice(0,2).join(' · '):'As diferenças não são fortes o suficiente para justificar a troca por si só.'};
  }
  function comparisonHTML(srcTk,dstTk){
    const a=stock(srcTk),b=stock(dstTk); if(!a||!b)return '';
    const v=verdict(a,b),pa=priceStats(a),pb=priceStats(b);
    return `<div class="ux456-compare-panel" data-ux456-pair="${esc(srcTk)}>${esc(dstTk)}">
      <div class="ux456-compare-head"><div><small>COMPARAÇÃO DIRETA</small><strong>${esc(srcTk)} <span>→</span> ${esc(dstTk)}</strong></div><span class="ux456-verdict is-${v.tone}">${esc(v.title)}</span></div>
      <div class="ux456-company-pair"><div><small>ATUAL</small><b>${esc(a.name||srcTk)}</b></div><i>→</i><div><small>ALTERNATIVA</small><b>${esc(b.name||dstTk)}</b></div></div>
      <div class="ux456-metrics">
        ${metric('Score Vestra',a.score,b.score)}
        ${metric('Timing',timing(a),timing(b))}
        ${metric('Confiança',a.confidence_score,b.confidence_score)}
        ${metric('ROE',a.roe,b.roe,pct,true)}
        ${metric('FCF yield',a.free_cash_flow_yield_pct,b.free_cash_flow_yield_pct,pct,true)}
        ${metric('Forward P/E',a.forward_pe,b.forward_pe,multiple,false)}
        ${metric('20 dias',pa.r20,pb.r20,x=>x==null?'—':`${x>=0?'+':''}${x.toFixed(1)}%`,true)}
        ${metric('Espaço até máx.',pa.room,pb.room,x=>x==null?'—':`${x.toFixed(0)}%`,true)}
      </div>
      <div class="ux456-verdict-copy is-${v.tone}"><b>${esc(v.title)}</b><span>${esc(v.text)}</span><small>O Vestra compara dimensões relevantes; isto não é uma ordem de compra ou venda.</small></div>
      <div class="ux456-actions"><button type="button" data-market-ticker="${esc(srcTk)}">Ver ${esc(srcTk)}</button><button type="button" data-market-ticker="${esc(dstTk)}">Ver ${esc(dstTk)}</button><button type="button" data-ux456-impact>Ver impacto na carteira</button></div>
    </div>`;
  }
  function installSwapLab(){
    const sh=document.getElementById('marketSheet'),root=document.getElementById('marketSheetContent');
    if(!sh||sh.hidden||t(sh.dataset.tool)!=='portfolio'||!root)return;
    const card=root.querySelector('[data-ux-kind="swap"]');if(!card||card.classList.contains('is-collapsed'))return;
    const cs=candidates(card);if(!cs.length)return;
    let lab=card.querySelector('.ux456-swaplab');
    if(!lab){lab=document.createElement('div');lab.className='ux456-swaplab';const anchor=card.querySelector('.ux454-swap-head')||card.querySelector('.ux453-badge');anchor?anchor.insertAdjacentElement('afterend',lab):card.prepend(lab);}
    const signature=cs.map(c=>`${c.source}>${c.target}`).join('|');if(lab.dataset.signature===signature)return;
    lab.dataset.signature=signature;
    const options=cs.map((c,i)=>`<button type="button" class="${i===0?'is-active':''}" data-ux456-pair="${esc(c.source)}|${esc(c.target)}"><b>${esc(c.source)}</b><span>→</span><strong>${esc(c.target)}</strong></button>`).join('');
    lab.innerHTML=`<div class="ux456-pair-picker"><small>ESCOLHER TROCA</small><div>${options}</div></div><div class="ux456-comparison-host">${comparisonHTML(cs[0].source,cs[0].target)}</div>`;
  }
  function polishOverlap(){
    const root=document.getElementById('marketSheetContent');const card=root?.querySelector('[data-ux-kind="overlap"]');if(!card)return;
    card.style.setProperty('padding-right','16px');
    const head=card.querySelector('.market-perspective-head');if(head)head.style.setProperty('padding-right','58px');
    const toggle=card.querySelector(':scope > .market-collapse-toggle');if(toggle){toggle.style.right='12px';toggle.style.top='12px';}
  }
  function addStyle(){
    if(document.getElementById('vestra-ux-v456-style'))return;
    const s=document.createElement('style');s.id='vestra-ux-v456-style';s.textContent=`
      .ux456-swaplab{margin:10px 0 14px;padding:12px;border:1px solid #ddd6f3;border-radius:18px;background:linear-gradient(145deg,#fbf9ff,#f5f1ff)}.ux456-pair-picker>small{font-size:8px;font-weight:900;letter-spacing:.12em;color:#6a55aa}.ux456-pair-picker>div{display:flex;gap:6px;overflow-x:auto;padding:7px 0 2px;scrollbar-width:none}.ux456-pair-picker button{flex:0 0 auto;border:1px solid #ddd6f3;background:white;color:#263b42;border-radius:999px;padding:7px 9px;font-size:10px;font-weight:800}.ux456-pair-picker button.is-active{background:#7664b7;color:white;border-color:#7664b7}.ux456-pair-picker button span{opacity:.55;margin:0 3px}
      .ux456-compare-panel{margin-top:10px;padding:12px;border-radius:16px;background:white;border:1px solid #e5e0f4}.ux456-compare-head{display:flex;justify-content:space-between;gap:10px;align-items:start}.ux456-compare-head>div{display:grid;gap:2px}.ux456-compare-head small{font-size:8px;letter-spacing:.1em;font-weight:900;color:#6a55aa}.ux456-compare-head strong{font-size:15px}.ux456-compare-head strong span{color:#8a7bc2}.ux456-verdict{font-size:8.5px;font-weight:850;padding:5px 7px;border-radius:999px;text-align:center;max-width:126px}.ux456-verdict.is-good{background:#e4f6ef;color:#167b60}.ux456-verdict.is-neutral{background:#edf1f3;color:#5f747b}.ux456-verdict.is-bad{background:#fbe9e5;color:#b35344}
      .ux456-company-pair{display:grid;grid-template-columns:1fr auto 1fr;gap:8px;align-items:center;margin:11px 0;padding:9px;border-radius:13px;background:#f8f7fb}.ux456-company-pair>div{display:grid;gap:2px}.ux456-company-pair small{font-size:7.5px;font-weight:900;letter-spacing:.1em;color:#839198}.ux456-company-pair b{font-size:10px;line-height:1.25}.ux456-company-pair i{font-style:normal;color:#8c7dc2;font-weight:900}
      .ux456-metrics{display:grid;gap:1px;border:1px solid #edf0f1;border-radius:13px;overflow:hidden}.ux456-metric{display:grid;grid-template-columns:minmax(90px,1fr) 54px 18px 54px;align-items:center;gap:4px;padding:8px 9px;background:#fff;border-bottom:1px solid #edf0f1;font-size:10px}.ux456-metric:last-child{border-bottom:0}.ux456-metric span{color:#6c7f86}.ux456-metric b,.ux456-metric strong{text-align:right}.ux456-metric i{text-align:center;font-style:normal;color:#a2afb4}.ux456-metric strong.is-better{color:#168a69}.ux456-metric strong.is-worse{color:#bc5d4c}
      .ux456-verdict-copy{display:grid;gap:3px;margin-top:10px;padding:10px;border-radius:13px}.ux456-verdict-copy.is-good{background:#eef9f5}.ux456-verdict-copy.is-neutral{background:#f3f6f7}.ux456-verdict-copy.is-bad{background:#fff2ef}.ux456-verdict-copy b{font-size:11px}.ux456-verdict-copy span{font-size:9.5px;color:#526970}.ux456-verdict-copy small{font-size:8px;color:#839198;margin-top:2px}.ux456-actions{display:flex;gap:6px;flex-wrap:wrap;margin-top:9px}.ux456-actions button{border:1px solid #d9dde0;background:#fff;border-radius:999px;padding:7px 9px;font-size:9.5px;font-weight:800;color:#27434b}.ux456-actions button:last-child{background:#7664b7;color:white;border-color:#7664b7}
      [data-ux-kind="swap"]>.market-collapse-toggle,[data-ux-kind="overlap"]>.market-collapse-toggle{z-index:5!important}.ux454-swap-head{padding-right:46px!important}.ux454-overlap-head{padding-right:46px!important}
      @media(max-width:620px){.ux456-compare-head{display:grid}.ux456-verdict{justify-self:start;max-width:none}.ux456-metric{grid-template-columns:minmax(82px,1fr) 48px 14px 48px;font-size:9.5px}.ux456-company-pair b{font-size:9px}}
    `;document.head.appendChild(s);
  }
  function apply(){installSwapLab();polishOverlap();}
  document.addEventListener('click',e=>{
    const pair=e.target.closest?.('[data-ux456-pair]');
    if(pair&&pair.closest('.ux456-pair-picker')){
      e.preventDefault();e.stopPropagation();const [src,dst]=t(pair.dataset.ux456Pair).split('|');
      const lab=pair.closest('.ux456-swaplab');lab.querySelectorAll('.ux456-pair-picker button').forEach(x=>x.classList.toggle('is-active',x===pair));
      const host=lab.querySelector('.ux456-comparison-host');if(host)host.innerHTML=comparisonHTML(src,dst);return;
    }
    const impact=e.target.closest?.('[data-ux456-impact]');
    if(impact){e.preventDefault();e.stopPropagation();const root=document.getElementById('marketSheetContent');const scenario=root?.querySelector('[data-ux-kind="scenario"]');if(scenario?.classList.contains('is-collapsed'))scenario.querySelector('[data-collapse-toggle]')?.click();setTimeout(()=>scenario?.scrollIntoView({behavior:'smooth',block:'start'}),30);}
  });
  function start(){addStyle();apply();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});});mo.observe(document.body,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
  window.VestraSwapLab=Object.freeze({stock,priceStats,timing,verdict,refresh:apply});
})();