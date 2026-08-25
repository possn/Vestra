/* Vestra Politicians v1.0 — STOCK Act explorer, Winston-inspired. */
(() => {
  'use strict';
  const VERSION='1.0';
  const t=v=>String(v??'').trim();
  const esc=v=>t(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let trades=[];
  let loading=null;
  let selected='';

  function workerBase(){
    try { return t(window.state?.settings?.workerUrl).replace(/\/$/,''); } catch { return ''; }
  }
  function normalize(x){
    const type=t(x?.type||x?.transaction||x?.transaction_type).toLowerCase();
    return {
      ticker:t(x?.ticker).toUpperCase(),
      representative:t(x?.representative||x?.member||x?.name)||'Membro do Congresso',
      chamber:t(x?.chamber), state:t(x?.state), party:t(x?.party),
      type, amount:t(x?.amount||x?.amount_range)||'—',
      transaction_date:t(x?.transaction_date||x?.date),
      disclosure_date:t(x?.disclosure_date||x?.filed_date||x?.filing_date),
      owner:t(x?.owner||x?.asset_owner),
      source:t(x?.source||'STOCK Act')
    };
  }
  function isBuy(x){ return /purchase|buy|compr/.test(t(x?.type).toLowerCase()); }
  function isSell(x){ return /sale|sell|vend/.test(t(x?.type).toLowerCase()); }
  function amountValue(v){
    const s=t(v).replace(/,/g,'');
    const nums=[...s.matchAll(/\$?([0-9]+(?:\.[0-9]+)?)([KMB])?/gi)].map(m=>{let n=Number(m[1]); const u=t(m[2]).toUpperCase(); if(u==='K')n*=1e3;if(u==='M')n*=1e6;if(u==='B')n*=1e9;return n;});
    if(!nums.length)return 0; return nums.reduce((a,b)=>a+b,0)/nums.length;
  }
  function shortMoney(v){
    const n=amountValue(v); if(!n)return t(v)||'—';
    return new Intl.NumberFormat('pt-PT',{notation:'compact',maximumFractionDigits:1,style:'currency',currency:'USD'}).format(n);
  }
  function shortDate(v){
    if(!v)return '—'; const d=new Date(v); if(Number.isNaN(d.valueOf()))return esc(v);
    return new Intl.DateTimeFormat('pt-PT',{day:'2-digit',month:'short',year:'numeric'}).format(d);
  }
  function cacheKey(){return 'vestra-politicians-v1';}
  async function load(){
    if(loading)return loading;
    loading=(async()=>{
      try{
        const cached=JSON.parse(localStorage.getItem(cacheKey())||'null');
        if(cached?.ts && Array.isArray(cached.trades) && Date.now()-cached.ts<15*60*1000){ trades=cached.trades.map(normalize); return trades; }
      }catch(_){}
      const from=new Date(Date.now()-365*86400000).toISOString().slice(0,10);
      const base=workerBase();
      const urls=[`https://www.bargo.ai/free-apis/congress/v1/trades?from=${from}&limit=500`,base?`${base}/congress?from=${from}&limit=500`:null].filter(Boolean);
      let last='';
      for(const url of urls){
        try{
          const r=await fetch(url,{cache:'no-store',mode:'cors'}); if(!r.ok){last=`HTTP ${r.status}`;continue;}
          const d=await r.json();
          const arr=Array.isArray(d)?d:(d?.trades||d?.data||[]);
          const out=arr.map(normalize).filter(x=>x.ticker&&x.representative);
          if(out.length){trades=out;try{localStorage.setItem(cacheKey(),JSON.stringify({ts:Date.now(),trades:out}));}catch(_){};return trades;}
        }catch(e){last=e?.message||String(e);}
      }
      throw new Error(last||'Sem dados do Congresso');
    })().finally(()=>{loading=null;});
    return loading;
  }
  function politicians(){
    const m=new Map();
    for(const x of trades){
      const k=x.representative; const p=m.get(k)||{name:k,chamber:x.chamber,state:x.state,party:x.party,count:0,buys:0,sells:0,last:''};
      p.count++; if(isBuy(x))p.buys++; if(isSell(x))p.sells++; if(x.disclosure_date>p.last)p.last=x.disclosure_date; m.set(k,p);
    }
    return [...m.values()].sort((a,b)=>b.count-a.count||a.name.localeCompare(b.name));
  }
  function profileRows(name){return trades.filter(x=>x.representative===name).sort((a,b)=>t(b.transaction_date).localeCompare(t(a.transaction_date)));}
  function topSide(rows,side){
    return rows.filter(side==='buy'?isBuy:isSell).sort((a,b)=>amountValue(b.amount)-amountValue(a.amount)).slice(0,10);
  }
  function bars(rows,side){
    const arr=topSide(rows,side); const max=Math.max(1,...arr.map(x=>amountValue(x.amount)));
    if(!arr.length)return '<p class="politician-empty">Sem operações deste tipo no período carregado.</p>';
    return arr.map(x=>`<button type="button" class="politician-bar" data-market-ticker="${esc(x.ticker)}"><span><strong>${esc(x.ticker)}</strong><small>${esc(shortDate(x.transaction_date))}</small></span><i><b style="width:${Math.max(7,amountValue(x.amount)/max*100)}%"></b></i><em>${esc(shortMoney(x.amount))}</em></button>`).join('');
  }
  function tradeList(rows){
    return rows.slice(0,80).map(x=>`<button type="button" class="politician-trade" data-market-ticker="${esc(x.ticker)}"><span><strong>${esc(x.ticker)}</strong><small>${esc(shortDate(x.transaction_date))}${x.owner?` · ${esc(x.owner)}`:''}</small></span><em class="${isBuy(x)?'is-buy':isSell(x)?'is-sell':''}">${isBuy(x)?'Compra':isSell(x)?'Venda':esc(x.type||'Trade')} · ${esc(x.amount)}</em></button>`).join('');
  }
  function render(){
    const root=document.getElementById('marketPrimary'); if(!root)return;
    const ps=politicians();
    if(!selected || !ps.some(p=>p.name===selected))selected=ps[0]?.name||'';
    const p=ps.find(x=>x.name===selected); const rows=profileRows(selected);
    const buys=rows.filter(isBuy).length,sells=rows.filter(isSell).length;
    const latest=rows.map(x=>x.disclosure_date||x.transaction_date).filter(Boolean).sort().reverse()[0];
    root.innerHTML=`<section class="market-section politicians-section"><div class="market-section__head"><div><h3>Políticos</h3><p>Compras e vendas declaradas ao abrigo do STOCK Act · escolhe um político para ver a atividade.</p></div><span class="market-data-age">${trades.length} trades</span></div>
      <div class="politician-picker"><label><span>Político</span><select data-politician-select>${ps.map(x=>`<option value="${esc(x.name)}" ${x.name===selected?'selected':''}>${esc(x.name)} · ${x.count} trades</option>`).join('')}</select></label></div>
      ${p?`<div class="politician-profile"><div><small>${esc([p.chamber,p.party,p.state].filter(Boolean).join(' · ')||'Congresso dos EUA')}</small><h3>${esc(p.name)}</h3><p>Divulgações públicas; podem ser comunicadas semanas depois da transação.</p></div><div class="politician-kpis"><span><small>Trades</small><strong>${rows.length}</strong></span><span><small>Compras</small><strong class="is-buy">${buys}</strong></span><span><small>Vendas</small><strong class="is-sell">${sells}</strong></span><span><small>Último filing</small><strong>${esc(shortDate(latest))}</strong></span></div></div>
      <div class="politician-sides"><section><div class="politician-side-head is-buy">↗ MAIORES COMPRAS <small>top 10</small></div>${bars(rows,'buy')}</section><section><div class="politician-side-head is-sell">↘ MAIORES VENDAS <small>top 10</small></div>${bars(rows,'sell')}</section></div>
      <div class="market-detail-card politician-all"><div class="market-perspective-head"><div><small>HISTÓRICO CARREGADO</small><h4>Todas as operações</h4></div><span class="market-data-age">${rows.length}</span></div>${tradeList(rows)||'<p>Sem operações.</p>'}</div>`:'<div class="market-empty">Sem políticos disponíveis no feed atual.</div>'}
      <p class="market-source-credit">Fonte: Bargo / divulgações STOCK Act. Valores são intervalos declarados; não representam necessariamente o montante exato executado.</p></section>`;
  }
  async function openPoliticians(){
    const root=document.getElementById('marketPrimary'); if(!root)return;
    document.querySelectorAll('.market-mode').forEach(x=>x.classList.remove('is-active'));
    document.querySelector('[data-politicians-mode]')?.classList.add('is-active');
    root.innerHTML='<div class="market-loader"><span></span><div>A carregar divulgações do Congresso…</div></div>';
    try{await load();render();}catch(e){root.innerHTML=`<div class="market-empty market-empty--error"><strong>Congresso indisponível</strong><br><span>${esc(e?.message||'Não foi possível carregar os dados.')}</span></div>`;}
  }
  function installButton(){
    const grid=document.querySelector('.market-mode-grid'); if(!grid||grid.querySelector('[data-politicians-mode]'))return;
    const btn=document.createElement('button'); btn.className='market-mode'; btn.type='button'; btn.dataset.politiciansMode='1'; btn.innerHTML='<span class="market-mode__icon">♜</span><strong>Políticos</strong>';
    const smart=grid.querySelector('[data-market-mode="smart"]'); smart?.insertAdjacentElement('afterend',btn) || grid.appendChild(btn);
  }
  function addStyle(){
    if(document.getElementById('vestra-politicians-style'))return;
    const s=document.createElement('style'); s.id='vestra-politicians-style'; s.textContent=`.politician-picker{margin:12px 0 16px}.politician-picker label{display:grid;gap:6px}.politician-picker span{font-size:11px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--text2)}.politician-picker select{width:100%;padding:12px 14px;border:1px solid var(--line);border-radius:14px;background:var(--card);color:var(--text);font:inherit}.politician-profile{display:grid;gap:14px;padding:18px;border:1px solid var(--line);border-radius:20px;background:var(--card);margin-bottom:14px}.politician-profile h3{margin:3px 0 4px}.politician-profile p{margin:0;color:var(--text2);font-size:12px}.politician-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.politician-kpis span{padding:10px;border-radius:12px;background:var(--soft);display:grid;gap:3px}.politician-kpis small{font-size:10px;color:var(--text2)}.politician-kpis strong{font-size:15px}.is-buy{color:#168f73!important}.is-sell{color:#c34f65!important}.politician-sides{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px}.politician-sides section{padding:14px;border:1px solid var(--line);border-radius:18px;background:var(--card)}.politician-side-head{font-size:11px;font-weight:900;letter-spacing:.06em;margin-bottom:10px}.politician-side-head small{font-weight:500;color:var(--text2)}.politician-bar{width:100%;display:grid;grid-template-columns:minmax(72px,1fr) minmax(80px,2fr) auto;gap:8px;align-items:center;background:none;border:0;padding:7px 0;color:var(--text);text-align:left}.politician-bar span{display:grid}.politician-bar small{color:var(--text2);font-size:9px}.politician-bar i{height:4px;border-radius:8px;background:var(--soft);overflow:hidden}.politician-bar b{display:block;height:100%;background:currentColor;border-radius:8px}.politician-side-head.is-buy+ .politician-bar i b{color:#21b28f}.politician-side-head.is-sell+ .politician-bar i b{color:#d95d72}.politician-bar em{font-style:normal;font-size:11px;font-weight:700}.politician-trade{width:100%;display:flex;justify-content:space-between;gap:12px;padding:11px 0;border:0;border-bottom:1px solid var(--line);background:none;color:var(--text);text-align:left}.politician-trade span{display:grid}.politician-trade small{color:var(--text2);font-size:10px}.politician-trade em{font-style:normal;font-size:11px;text-align:right}.politician-empty{font-size:11px;color:var(--text2)}@media(max-width:620px){.politician-sides{grid-template-columns:1fr}.politician-kpis{grid-template-columns:1fr 1fr}.politician-bar{grid-template-columns:74px 1fr auto}}`;
    document.head.appendChild(s);
  }
  document.addEventListener('click',e=>{
    const b=e.target.closest?.('[data-politicians-mode]'); if(!b)return;
    e.preventDefault(); e.stopPropagation(); openPoliticians();
  });
  document.addEventListener('change',e=>{
    if(!e.target.matches?.('[data-politician-select]'))return;
    selected=e.target.value; render();
  });
  function start(){addStyle();installButton(); let pending=false; const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;installButton();});});mo.observe(document.body,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();