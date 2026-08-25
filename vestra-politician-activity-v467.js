/* Vestra Politician Activity v4.67 — grouped ledger + functional following. */
(() => {
  'use strict';
  const t=v=>String(v??'').trim();
  const esc=v=>t(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const BUY=/purchase|buy|compr/i, SELL=/sale|sell|vend/i;
  const FOLLOW_KEY='vestra-politician-follows-v2';
  let pending=false;

  const isBuy=x=>BUY.test(t(x?.type));
  const isSell=x=>SELL.test(t(x?.type));
  function fmtDate(v){if(!v)return '—';const d=new Date(v);return Number.isNaN(d.valueOf())?t(v):new Intl.DateTimeFormat('pt-PT',{day:'2-digit',month:'2-digit',year:'numeric'}).format(d);}
  function getSection(){return document.querySelector('.politicians-section');}
  function getSelect(section=getSection()){return section?.querySelector('[data-politician-select]')||null;}
  function current(section=getSection()){
    const sel=getSelect(section);if(!sel)return {value:'',label:''};
    return {value:t(sel.value),label:t(sel.selectedOptions?.[0]?.textContent).split(' · ')[0]};
  }
  function getFollows(){try{return JSON.parse(localStorage.getItem(FOLLOW_KEY)||'[]').filter(x=>x&&x.value&&x.label)}catch{return[];}}
  function setFollows(rows){try{localStorage.setItem(FOLLOW_KEY,JSON.stringify(rows))}catch{}}
  function followed(value){return getFollows().some(x=>x.value===value);}

  function installControls(section){
    const picker=section.querySelector('.politician-picker');if(!picker)return;
    let controls=section.querySelector('.ux-politician-controls');
    if(!controls){controls=document.createElement('div');controls.className='ux-politician-controls';picker.insertAdjacentElement('afterend',controls);}
    if(controls.dataset.v467!=='1'){
      controls.dataset.v467='1';
      controls.innerHTML='<button class="is-active" data-v467-view="all">Tudo</button><button data-v467-view="buy">↗ Compras</button><button data-v467-view="sell">↘ Vendas</button><button data-v467-follow>☆ Seguir</button>';
      section.dataset.v467View='all';
    }
    updateFollowButton(section);
    renderFollowShelf(section);
  }

  function updateFollowButton(section){
    const b=section.querySelector('[data-v467-follow]');if(!b)return;
    const c=current(section),on=followed(c.value);
    b.textContent=on?'★ A seguir':'☆ Seguir';b.classList.toggle('is-fav',on);
  }

  function renderFollowShelf(section){
    const controls=section.querySelector('.ux-politician-controls');if(!controls)return;
    let shelf=section.querySelector('.ux467-followed');
    const rows=getFollows();
    if(!rows.length){shelf?.remove();return;}
    if(!shelf){shelf=document.createElement('div');shelf.className='ux467-followed';controls.insertAdjacentElement('afterend',shelf);}
    shelf.innerHTML=`<span>A SEGUIR</span><div>${rows.map(x=>`<button type="button" data-v467-followed="${esc(x.value)}">${esc(x.label)}</button>`).join('')}</div>`;
  }

  function parseRows(box){try{return JSON.parse(box.dataset.rows||'[]')}catch{return[];}}
  function filteredRows(section,rows){
    const view=t(section.dataset.v467View||'all');
    return rows.filter(x=>view==='all'||(view==='buy'&&isBuy(x))||(view==='sell'&&isSell(x)));
  }
  function groupRows(rows){
    const m=new Map();
    rows.forEach(x=>{
      const key=t(x.ticker)||t(x.asset)||'—';
      const g=m.get(key)||{ticker:t(x.ticker)||'—',asset:t(x.asset),rows:[],buys:0,sells:0,latest:''};
      g.rows.push(x);if(isBuy(x))g.buys++;if(isSell(x))g.sells++;
      const d=t(x.transaction_date||x.disclosure_date);if(d>g.latest)g.latest=d;
      if(!g.asset&&t(x.asset))g.asset=t(x.asset);m.set(key,g);
    });
    return [...m.values()].sort((a,b)=>t(b.latest).localeCompare(t(a.latest))||b.rows.length-a.rows.length||a.ticker.localeCompare(b.ticker));
  }
  function tradeLine(x){
    const verb=isBuy(x)?'Compra':isSell(x)?'Venda':(t(x.type)||'Operação');
    return `<button type="button" class="ux467-trade ${isBuy(x)?'is-buy':isSell(x)?'is-sell':''}" data-market-ticker="${esc(x.ticker)}"><span><b>${esc(verb)}</b><small>${esc(fmtDate(x.transaction_date))}${x.disclosure_date?` · divulgado ${esc(fmtDate(x.disclosure_date))}`:''}</small></span><em>${esc(x.amount||'—')}</em></button>`;
  }
  function groupCard(g){
    const bias=g.buys>g.sells?'is-buy':g.sells>g.buys?'is-sell':'';
    const summary=[g.buys?`${g.buys} compra${g.buys===1?'':'s'}`:'',g.sells?`${g.sells} venda${g.sells===1?'':'s'}`:''].filter(Boolean).join(' · ');
    return `<article class="ux467-group ${bias}" data-v467-group="${esc(g.ticker)}"><button type="button" class="ux467-group-head" data-v467-toggle><span><b>${esc(g.ticker)}</b><small>${esc(g.asset||'')} ${g.latest?`· ${esc(fmtDate(g.latest))}`:''}</small></span><span><strong>${g.rows.length} op.</strong><em>${esc(summary||'atividade')}</em></span><i>＋</i></button><div class="ux467-group-detail" hidden>${g.rows.map(tradeLine).join('')}</div></article>`;
  }

  function enhanceLedger(section){
    const box=section.querySelector('.ux466-ledger');if(!box)return;
    const rows=parseRows(box);if(!rows.length)return;
    // Keep v4.66 as data source, but replace the repetitive flat list with a grouped activity view.
    box.querySelector('.ux466-tabs')?.setAttribute('hidden','');
    box.querySelector('.ux466-list')?.setAttribute('hidden','');
    box.querySelector('[data-ux466-more]')?.setAttribute('hidden','');
    let host=box.querySelector('.ux467-ledger');if(!host){host=document.createElement('div');host.className='ux467-ledger';const tabs=box.querySelector('.ux466-tabs');tabs?.insertAdjacentElement('afterend',host)||box.appendChild(host);}
    const view=t(section.dataset.v467View||'all');const filtered=filteredRows(section,rows);const groups=groupRows(filtered);
    const sig=`${view}|${filtered.length}|${groups.map(g=>`${g.ticker}:${g.rows.length}`).join(',')}`;if(host.dataset.sig===sig)return;host.dataset.sig=sig;
    const label=view==='buy'?'Compras':view==='sell'?'Vendas':'Todas as operações';
    host.innerHTML=`<div class="ux467-ledger-head"><div><small>ATIVIDADE COMPLETA</small><strong>${esc(label)}</strong><span>Agrupada por empresa para não repetir o mesmo ticker dezenas de vezes. Abre uma empresa para ver cada operação.</span></div><span>${filtered.length} operações · ${groups.length} empresas</span></div><div class="ux467-groups">${groups.map(groupCard).join('')||'<p class="ux467-empty">Sem operações deste tipo.</p>'}</div>`;
  }

  function apply(){const section=getSection();if(!section)return;installControls(section);enhanceLedger(section);}

  function style(){if(document.getElementById('vestra-politician-activity-v467-style'))return;const s=document.createElement('style');s.id='vestra-politician-activity-v467-style';s.textContent=`
    .ux467-followed{display:flex;align-items:center;gap:8px;margin:-4px 0 12px;overflow:hidden}.ux467-followed>span{font-size:7.5px;letter-spacing:.12em;font-weight:900;color:var(--text2);flex:0 0 auto}.ux467-followed>div{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none}.ux467-followed button{white-space:nowrap;border:1px solid var(--line);background:var(--soft);color:var(--text);border-radius:999px;padding:6px 9px;font-size:9px;font-weight:800}.ux-politician-controls [data-v467-follow].is-fav{color:#9a6819!important;background:#fff8df!important;border-color:#ecd9a2!important}
    .ux467-ledger{display:grid;gap:10px}.ux467-ledger-head{display:flex;justify-content:space-between;align-items:start;gap:10px;padding:2px 0 5px}.ux467-ledger-head>div{display:grid;gap:2px}.ux467-ledger-head small{font-size:8px;letter-spacing:.12em;font-weight:900;color:var(--accent,#168e89)}.ux467-ledger-head strong{font-size:14px}.ux467-ledger-head>div>span{font-size:9px;color:var(--text2);line-height:1.35}.ux467-ledger-head>span{font-size:8px;color:var(--text2);white-space:nowrap;padding:5px 7px;border-radius:999px;background:var(--soft)}.ux467-groups{display:grid;gap:7px}.ux467-group{border:1px solid var(--line);border-radius:14px;overflow:hidden;background:var(--card)}.ux467-group.is-buy{box-shadow:inset 3px 0 0 rgba(22,143,115,.75)}.ux467-group.is-sell{box-shadow:inset 3px 0 0 rgba(195,79,101,.75)}.ux467-group-head{width:100%;display:grid;grid-template-columns:minmax(0,1fr) auto 24px;gap:8px;align-items:center;border:0;background:transparent;color:var(--text);padding:10px 11px;text-align:left}.ux467-group-head>span{display:grid;gap:1px;min-width:0}.ux467-group-head>span:nth-child(2){text-align:right}.ux467-group-head b{font-size:12px}.ux467-group-head small,.ux467-group-head em{font-size:8.5px;color:var(--text2);font-style:normal;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.ux467-group-head strong{font-size:9px}.ux467-group-head i{font-style:normal;font-size:16px;color:var(--text2);text-align:center}.ux467-group-detail{border-top:1px solid var(--line);padding:2px 11px 5px;background:color-mix(in srgb,var(--soft) 58%,var(--card))}.ux467-trade{width:100%;display:flex;justify-content:space-between;gap:10px;border:0;border-bottom:1px solid var(--line);background:transparent;color:var(--text);padding:9px 0;text-align:left}.ux467-trade:last-child{border-bottom:0}.ux467-trade span{display:grid;gap:1px}.ux467-trade b{font-size:9px}.ux467-trade small{font-size:8px;color:var(--text2)}.ux467-trade em{font-size:9px;font-style:normal;color:var(--text2);text-align:right}.ux467-trade.is-buy b{color:#168f73}.ux467-trade.is-sell b{color:#c34f65}.ux467-empty{padding:14px 0;color:var(--text2);font-size:10px}
    @media(max-width:620px){.ux467-ledger-head{display:grid}.ux467-ledger-head>span{justify-self:start}.ux467-group-head{grid-template-columns:minmax(0,1fr) auto 20px}}
  `;document.head.appendChild(s);}

  document.addEventListener('click',e=>{
    const view=e.target.closest?.('[data-v467-view]');if(view){const section=getSection();if(!section)return;e.preventDefault();e.stopPropagation();section.dataset.v467View=view.dataset.v467View;section.querySelectorAll('[data-v467-view]').forEach(x=>x.classList.toggle('is-active',x===view));enhanceLedger(section);return;}
    const follow=e.target.closest?.('[data-v467-follow]');if(follow){const section=getSection();if(!section)return;e.preventDefault();e.stopPropagation();const c=current(section);if(!c.value)return;let rows=getFollows();const idx=rows.findIndex(x=>x.value===c.value);if(idx>=0)rows.splice(idx,1);else rows.unshift(c);setFollows(rows);updateFollowButton(section);renderFollowShelf(section);return;}
    const f=e.target.closest?.('[data-v467-followed]');if(f){const section=getSection(),sel=getSelect(section);if(!sel)return;e.preventDefault();e.stopPropagation();sel.value=f.dataset.v467Followed;sel.dispatchEvent(new Event('change',{bubbles:true}));return;}
    const tog=e.target.closest?.('[data-v467-toggle]');if(tog){e.preventDefault();const card=tog.closest('.ux467-group'),detail=card?.querySelector('.ux467-group-detail'),icon=tog.querySelector('i');if(!detail)return;const open=detail.hidden;detail.hidden=!open;if(icon)icon.textContent=open?'−':'＋';}
  },true);
  document.addEventListener('change',e=>{if(!e.target.matches?.('[data-politician-select]'))return;const section=getSection();if(!section)return;section.dataset.v467View='all';setTimeout(()=>{installControls(section);section.querySelectorAll('[data-v467-view]').forEach(x=>x.classList.toggle('is-active',x.dataset.v467View==='all'));apply();},120);},true);

  function start(){style();apply();const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});});mo.observe(document.body,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
