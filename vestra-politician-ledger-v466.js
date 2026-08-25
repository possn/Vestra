/* Vestra Politician Ledger v4.66 — full available transaction history, not only summaries. */
(() => {
  'use strict';
  const t=v=>String(v??'').trim();
  const esc=v=>t(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const BUY=/purchase|buy|compr/i, SELL=/sale|sell|vend/i;
  const cache=new Map();
  let seq=0;

  function normalize(x){
    return {
      ticker:t(x?.ticker).toUpperCase(), asset:t(x?.asset||x?.security||x?.company),
      type:t(x?.type||x?.transaction||x?.transaction_type).toLowerCase(),
      amount:t(x?.amount||x?.amount_range)||'—',
      transaction_date:t(x?.transaction_date||x?.date), disclosure_date:t(x?.disclosure_date||x?.filed_date||x?.filing_date),
      representative:t(x?.representative||x?.member||x?.name), source:t(x?.source)||'Bargo / STOCK Act'
    };
  }
  const isBuy=x=>BUY.test(t(x?.type));
  const isSell=x=>SELL.test(t(x?.type));
  function fmtDate(v){if(!v)return '—';const d=new Date(v);return Number.isNaN(d.valueOf())?t(v):new Intl.DateTimeFormat('pt-PT',{day:'2-digit',month:'2-digit',year:'numeric'}).format(d);}
  function sig(x){return [x.ticker,x.type,x.amount,x.transaction_date,x.disclosure_date].join('|');}

  async function fetchCongress(slug,name){
    const key=`${slug}|${name}`;if(cache.has(key))return cache.get(key);
    const base='https://www.bargo.ai/free-apis/congress/v1/trades';
    let all=[];
    // The free Bargo distribution exposes the rolling 3-month window. Fetch the member-filtered feed
    // page-by-page so the UI shows the full available window rather than only the summary/top 10.
    for(let page=0;page<5;page++){
      let data=null;
      for(const member of [slug,name].filter(Boolean)){
        try{
          const r=await fetch(`${base}?member=${encodeURIComponent(member)}&limit=100&page=${page}`,{cache:'no-store',mode:'cors'});
          if(r.ok){data=await r.json();break;}
        }catch(_){ }
      }
      if(!data)break;
      const arr=Array.isArray(data)?data:(data?.trades||data?.data||[]);
      const rows=arr.map(normalize).filter(x=>x.ticker);
      all.push(...rows);
      const reported=Number(data?.count||0);
      if(rows.length<100 || (reported && all.length>=reported))break;
    }
    const seen=new Set();all=all.filter(x=>{const k=sig(x);if(seen.has(k))return false;seen.add(k);return true;});
    all.sort((a,b)=>t(b.transaction_date).localeCompare(t(a.transaction_date))||t(b.disclosure_date).localeCompare(t(a.disclosure_date)));
    cache.set(key,all);return all;
  }

  function row(x){
    const cls=isBuy(x)?'is-buy':isSell(x)?'is-sell':'';
    const verb=isBuy(x)?'Compra':isSell(x)?'Venda':(t(x.type)||'Operação');
    return `<button type="button" class="ux466-ledger-row ${cls}" data-market-ticker="${esc(x.ticker)}"><span class="ux466-ledger-main"><b>${esc(x.ticker)}</b><small>${esc(x.asset||'')} ${x.transaction_date?'· '+esc(fmtDate(x.transaction_date)):''}</small></span><span class="ux466-ledger-side"><strong>${esc(verb)}</strong><em>${esc(x.amount)}</em>${x.disclosure_date?`<small>divulgado ${esc(fmtDate(x.disclosure_date))}</small>`:''}</span></button>`;
  }

  function renderLedger(section,rows,meta={}){
    let box=section.querySelector('.ux466-ledger');
    if(!box){box=document.createElement('div');box.className='ux466-ledger';const profile=document.getElementById('politicianProfile');profile?.appendChild(box);}
    const buys=rows.filter(isBuy).length,sells=rows.filter(isSell).length;
    box.dataset.view='all';box.dataset.limit='25';box.dataset.rows=JSON.stringify(rows);
    box.innerHTML=`<div class="ux466-head"><div><small>HISTÓRICO DE OPERAÇÕES</small><strong>${meta.executive?'Operações disponíveis neste filing':'Todas as operações disponíveis'}</strong><span>${meta.subtitle||'Janela pública disponível na fonte.'}</span></div><span>${rows.length} operações</span></div>
      <div class="ux466-tabs"><button class="is-active" data-ux466-view="all">Todas <b>${rows.length}</b></button><button data-ux466-view="buy">Compras <b>${buys}</b></button><button data-ux466-view="sell">Vendas <b>${sells}</b></button></div>
      <div class="ux466-list"></div><button type="button" class="ux466-more" data-ux466-more hidden>Mostrar mais</button>${meta.note?`<p class="ux466-note">${meta.note}</p>`:''}${meta.sourceUrl?`<a class="ux466-source" href="${esc(meta.sourceUrl)}" target="_blank" rel="noopener">Abrir filing oficial completo ↗</a>`:''}`;
    paint(box);
  }

  function paint(box){
    let rows=[];try{rows=JSON.parse(box.dataset.rows||'[]')}catch{}
    const view=box.dataset.view||'all';const limit=Number(box.dataset.limit||25);
    const filtered=rows.filter(x=>view==='all'||(view==='buy'&&isBuy(x))||(view==='sell'&&isSell(x)));
    box.querySelector('.ux466-list').innerHTML=filtered.slice(0,limit).map(row).join('')||'<p class="ux466-empty">Sem operações deste tipo no período carregado.</p>';
    const more=box.querySelector('[data-ux466-more]');if(more){more.hidden=filtered.length<=limit;more.textContent=`Mostrar mais (${Math.min(25,filtered.length-limit)} de ${filtered.length-limit})`;}
    box.querySelectorAll('[data-ux466-view]').forEach(b=>b.classList.toggle('is-active',b.dataset.ux466View===view));
  }

  async function hydrate(){
    const section=document.querySelector('.politicians-section');const sel=section?.querySelector('[data-politician-select]');const profile=document.getElementById('politicianProfile');if(!section||!sel||!profile)return;
    const token=++seq;const value=t(sel.value);const label=t(sel.selectedOptions?.[0]?.textContent).split(' · ')[0];
    // Remove stale ledger immediately when switching politicians.
    section.querySelector('.ux466-ledger')?.remove();
    if(value.startsWith('congress:')){
      const slug=value.slice('congress:'.length);
      let loading=document.createElement('div');loading.className='ux466-loading';loading.textContent='A carregar todas as operações disponíveis…';profile.appendChild(loading);
      const rows=await fetchCongress(slug,label);if(token!==seq)return;loading.remove();
      renderLedger(section,rows,{subtitle:'Histórico individual da janela gratuita Bargo/STOCK Act (últimos ~3 meses).'});
      return;
    }
    if(value==='executive:donald-trump'){
      // politicians.js currently carries only filing highlights for the executive profile. Surface every
      // row actually ingested and make the limitation explicit instead of presenting it as complete history.
      const rows=[...profile.querySelectorAll('.politician-trade')].map(el=>{
        const em=el.querySelector('em'),sm=el.querySelector('small');const parts=t(em?.textContent).split(' · ');
        return {ticker:t(el.dataset.marketTicker),asset:t(sm?.textContent).split('·')[0],type:/compra/i.test(parts[0])?'purchase':/venda/i.test(parts[0])?'sale':parts[0],amount:parts.slice(1).join(' · ')||'—',transaction_date:'',disclosure_date:'2026-08-22'};
      }).filter(x=>x.ticker);
      renderLedger(section,rows,{executive:true,subtitle:'Linhas já ingeridas do OGE Form 278-T.',note:'O filing presidencial contém 1.000+ transações. O Vestra ainda só tem as linhas destacadas ingeridas; por isso não as apresenta como histórico completo.',sourceUrl:'https://extapps2.oge.gov/201/Presiden.nsf/PAS%2BIndex/405E4EC4E27BE8D185258DF7002DD1C0/%24FILE/Trump%2C%20Donald%20J.-05.08.2026-278T%282%29.pdf'});
    }
  }

  function style(){if(document.getElementById('vestra-politician-ledger-v466-style'))return;const s=document.createElement('style');s.id='vestra-politician-ledger-v466-style';s.textContent=`
    .ux466-ledger{margin:14px 0;padding:14px;border:1px solid var(--line);border-radius:20px;background:var(--card);box-shadow:0 8px 22px rgba(18,48,54,.045)}.ux466-head{display:flex;justify-content:space-between;gap:10px;align-items:start;margin-bottom:10px}.ux466-head>div{display:grid;gap:2px}.ux466-head small{font-size:8px;letter-spacing:.12em;font-weight:900;color:var(--accent,#168e89)}.ux466-head strong{font-size:15px}.ux466-head span{font-size:9px;color:var(--text2)}.ux466-head>span{padding:5px 8px;border-radius:999px;background:var(--soft);white-space:nowrap}.ux466-tabs{display:flex;gap:6px;overflow:auto;margin-bottom:8px}.ux466-tabs button{border:1px solid var(--line);border-radius:999px;background:var(--soft);padding:7px 10px;color:var(--text2);font-size:9px;font-weight:850;white-space:nowrap}.ux466-tabs button.is-active{background:#165f6c;color:white;border-color:#165f6c}.ux466-tabs b{margin-left:3px}.ux466-list{display:grid}.ux466-ledger-row{display:flex;justify-content:space-between;gap:12px;width:100%;padding:11px 2px;border:0;border-bottom:1px solid var(--line);background:transparent;color:var(--text);text-align:left}.ux466-ledger-main,.ux466-ledger-side{display:grid;gap:2px}.ux466-ledger-main{min-width:0}.ux466-ledger-main b{font-size:12px}.ux466-ledger-main small,.ux466-ledger-side small{font-size:8.5px;color:var(--text2)}.ux466-ledger-side{text-align:right;flex:0 0 auto}.ux466-ledger-side strong{font-size:9px}.ux466-ledger-side em{font-size:9px;font-style:normal;color:var(--text2)}.ux466-ledger-row.is-buy .ux466-ledger-side strong{color:#168f73}.ux466-ledger-row.is-sell .ux466-ledger-side strong{color:#c34f65}.ux466-more{width:100%;margin-top:10px;border:1px solid var(--line);border-radius:12px;padding:10px;background:var(--soft);color:var(--text);font-weight:800}.ux466-note{font-size:9px;line-height:1.45;color:var(--text2);background:var(--soft);border-radius:12px;padding:10px;margin:10px 0 0}.ux466-source{display:inline-block;margin-top:9px;font-size:9px;font-weight:800;color:var(--accent,#168e89);text-decoration:none}.ux466-loading{margin:12px 0;padding:12px;border-radius:14px;background:var(--soft);font-size:10px;color:var(--text2)}.ux466-empty{padding:14px 0;color:var(--text2);font-size:10px}
  `;document.head.appendChild(s);}

  document.addEventListener('click',e=>{const b=e.target.closest?.('[data-ux466-view]');if(b){const box=b.closest('.ux466-ledger');box.dataset.view=b.dataset.ux466View;box.dataset.limit='25';paint(box);return;}const more=e.target.closest?.('[data-ux466-more]');if(more){const box=more.closest('.ux466-ledger');box.dataset.limit=String(Number(box.dataset.limit||25)+25);paint(box);}},true);
  document.addEventListener('change',e=>{if(e.target.matches?.('[data-politician-select]'))setTimeout(hydrate,80);},true);
  function start(){style();hydrate();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;const section=document.querySelector('.politicians-section');if(section&&!section.querySelector('.ux466-ledger')&&!section.querySelector('.ux466-loading'))hydrate();});});mo.observe(document.body,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
