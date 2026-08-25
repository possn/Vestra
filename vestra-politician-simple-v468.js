/* Vestra Politicians v4.68 — one simple activity view + reliable follow. */
(() => {
  'use strict';
  const FOLLOW_KEY='vestra-politician-follows-v3';
  const t=v=>String(v??'').trim();
  const BUY=/purchase|buy|compr/i, SELL=/sale|sell|vend/i;
  let pending=false;
  const isBuy=x=>BUY.test(t(x?.type));
  const isSell=x=>SELL.test(t(x?.type));
  const fmtDate=v=>{if(!v)return '—';const d=new Date(v);return Number.isNaN(d.valueOf())?t(v):new Intl.DateTimeFormat('pt-PT',{day:'2-digit',month:'2-digit',year:'numeric'}).format(d)};
  const getSection=()=>document.querySelector('.politicians-section');
  const getSelect=s=>s?.querySelector('[data-politician-select]');
  function current(section){const sel=getSelect(section);return {value:t(sel?.value),label:t(sel?.selectedOptions?.[0]?.textContent).split(' · ')[0]};}
  function readFollows(){try{return JSON.parse(localStorage.getItem(FOLLOW_KEY)||'[]').filter(x=>x?.value&&x?.label)}catch{return[]}}
  function writeFollows(rows){try{localStorage.setItem(FOLLOW_KEY,JSON.stringify(rows))}catch{}}
  function rowsFromLedger(section){const box=section?.querySelector('.ux466-ledger');if(!box)return[];try{return JSON.parse(box.dataset.rows||'[]')}catch{return[]}}
  function esc(v){return t(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
  function row(x){const buy=isBuy(x),sell=isSell(x);const verb=buy?'Compra':sell?'Venda':'Operação';return `<button type="button" class="ux468-trade ${buy?'is-buy':sell?'is-sell':''}" data-market-ticker="${esc(x.ticker)}"><span><b>${esc(x.ticker||'—')}</b><small>${esc(x.asset||'')}${x.transaction_date?' · '+esc(fmtDate(x.transaction_date)):''}</small></span><span><strong>${verb}</strong><em>${esc(x.amount||'—')}</em>${x.disclosure_date?`<small>divulgado ${esc(fmtDate(x.disclosure_date))}</small>`:''}</span></button>`;}
  function cleanup(section){
    section.querySelectorAll('.ux-politician-controls,.ux467-followed,.ux467-ledger,.ux-politician-pulse,.politician-callout,.politician-sides,.politician-all').forEach(x=>x.remove());
    // v4.66 stays mounted only as a hidden data source.
    const ledger=section.querySelector('.ux466-ledger');if(ledger)ledger.hidden=true;
    // Keep only one Political Flow summary if old observers create duplicates.
    const flow=[...section.querySelectorAll('*')].filter(x=>/O que o Congresso está a negociar agora/i.test(t(x.querySelector?.('h3,h4,strong')?.textContent||x.textContent))&&x.querySelector?.('h3,h4,strong'));
    const cards=[];flow.forEach(x=>{let p=x;while(p&&p!==section&&!p.matches?.('.market-detail-card,.ux-political-flow,.political-flow-card'))p=p.parentElement;if(p&&p!==section&&!cards.includes(p))cards.push(p);});cards.slice(1).forEach(x=>x.remove());
  }
  function render(section){
    const picker=section.querySelector('.politician-picker');const profile=document.getElementById('politicianProfile');if(!picker||!profile)return;
    cleanup(section);
    const c=current(section),follows=readFollows(),on=follows.some(x=>x.value===c.value);
    const rows=rowsFromLedger(section).slice().sort((a,b)=>t(b.transaction_date||b.disclosure_date).localeCompare(t(a.transaction_date||a.disclosure_date)));
    let controls=section.querySelector('.ux468-controls');if(!controls){controls=document.createElement('div');controls.className='ux468-controls';picker.insertAdjacentElement('afterend',controls);}
    controls.innerHTML=`<button type="button" data-ux468-follow class="${on?'is-on':''}">${on?'★ A seguir':'☆ Seguir'}</button>${follows.length?`<div class="ux468-followed"><span>A seguir</span>${follows.map(x=>`<button type="button" data-ux468-pick="${esc(x.value)}">${esc(x.label)}</button>`).join('')}</div>`:''}`;
    let activity=profile.querySelector('.ux468-activity');if(!activity){activity=document.createElement('section');activity.className='ux468-activity';profile.appendChild(activity);}
    const buys=rows.filter(isBuy).slice(0,10),sells=rows.filter(isSell).slice(0,10);
    activity.innerHTML=`<div class="ux468-head"><small>ÚLTIMAS DIVULGAÇÕES</small><h4>Compras e vendas notificadas</h4><p>Mostra apenas as operações mais recentes disponíveis para este político.</p></div><div class="ux468-cols"><div><h5>↗ Últimas compras</h5>${buys.map(row).join('')||'<p class="ux468-empty">Sem compras recentes disponíveis.</p>'}</div><div><h5>↘ Últimas vendas</h5>${sells.map(row).join('')||'<p class="ux468-empty">Sem vendas recentes disponíveis.</p>'}</div></div>`;
  }
  function apply(){const s=getSection();if(!s)return;render(s);}
  function style(){if(document.getElementById('vestra-politician-simple-v468-style'))return;const s=document.createElement('style');s.id='vestra-politician-simple-v468-style';s.textContent=`
    .ux468-controls{display:grid;gap:8px;margin:-6px 0 12px}.ux468-controls>button{justify-self:start;border:1px solid var(--line);border-radius:999px;background:var(--card);padding:8px 12px;font-weight:850;color:var(--text2)}.ux468-controls>button.is-on{background:#fff8df;color:#946516;border-color:#ead79d}.ux468-followed{display:flex;align-items:center;gap:6px;overflow:auto}.ux468-followed>span{font-size:8px;font-weight:900;letter-spacing:.12em;color:var(--text2);text-transform:uppercase;flex:0 0 auto}.ux468-followed button{white-space:nowrap;border:1px solid var(--line);background:var(--soft);border-radius:999px;padding:6px 9px;color:var(--text);font-size:9px;font-weight:800}
    .ux468-activity{margin-top:14px;padding:14px;border:1px solid var(--line);border-radius:18px;background:var(--card)}.ux468-head{display:grid;gap:2px;margin-bottom:10px}.ux468-head small{font-size:8px;letter-spacing:.13em;font-weight:900;color:var(--accent,#168e89)}.ux468-head h4{margin:0;font-size:17px}.ux468-head p{margin:0;color:var(--text2);font-size:10px}.ux468-cols{display:grid;grid-template-columns:1fr 1fr;gap:14px}.ux468-cols>div{min-width:0}.ux468-cols h5{margin:0 0 6px;font-size:11px}.ux468-trade{width:100%;display:flex;justify-content:space-between;gap:10px;padding:9px 0;border:0;border-bottom:1px solid var(--line);background:none;color:var(--text);text-align:left}.ux468-trade:last-child{border-bottom:0}.ux468-trade>span{display:grid;gap:2px;min-width:0}.ux468-trade>span:last-child{text-align:right;flex:0 0 auto}.ux468-trade b{font-size:11px}.ux468-trade strong{font-size:9px}.ux468-trade small,.ux468-trade em{font-size:8.5px;color:var(--text2);font-style:normal}.ux468-trade.is-buy strong{color:#168f73}.ux468-trade.is-sell strong{color:#c34f65}.ux468-empty{font-size:10px;color:var(--text2);padding:8px 0}
    @media(max-width:620px){.ux468-cols{grid-template-columns:1fr}.ux468-activity{padding:12px}}
  `;document.head.appendChild(s);}
  document.addEventListener('click',e=>{const s=getSection();if(!s)return;const follow=e.target.closest?.('[data-ux468-follow]');if(follow){e.preventDefault();e.stopPropagation();const c=current(s);let rows=readFollows();const i=rows.findIndex(x=>x.value===c.value);if(i>=0)rows.splice(i,1);else rows.unshift(c);writeFollows(rows);render(s);return;}const pick=e.target.closest?.('[data-ux468-pick]');if(pick){const sel=getSelect(s);if(!sel)return;sel.value=pick.dataset.ux468Pick;sel.dispatchEvent(new Event('change',{bubbles:true}));}},true);
  document.addEventListener('change',e=>{if(e.target.matches?.('[data-politician-select]'))setTimeout(apply,180);},true);
  function start(){style();apply();const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});});mo.observe(document.body,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();