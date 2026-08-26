/* Vestra Politicians v2.0 — canonical local STOCK Act snapshot. */
(() => {
  'use strict';
  const VERSION='2.0';
  const t=v=>String(v??'').trim();
  const esc=v=>t(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let recentTrades=[];
  let memberDirectory=[];
  let selected='';
  let feedMeta={};
  let loading=null;

  const isBuy=x=>/purchase|buy|compr/.test(t(x?.type).toLowerCase());
  const isSell=x=>/sale|sell|vend/.test(t(x?.type).toLowerCase());
  function amountValue(v){const s=t(v).replace(/,/g,'');const nums=[...s.matchAll(/\$?([0-9]+(?:\.[0-9]+)?)([KMB])?/gi)].map(m=>{let n=Number(m[1]);const u=t(m[2]).toUpperCase();if(u==='K')n*=1e3;if(u==='M')n*=1e6;if(u==='B')n*=1e9;return n;});return nums.length?nums.reduce((a,b)=>a+b,0)/nums.length:0;}
  function shortMoney(v){const n=amountValue(v);return n?new Intl.NumberFormat('pt-PT',{notation:'compact',maximumFractionDigits:1,style:'currency',currency:'USD'}).format(n):(t(v)||'—');}
  function shortDate(v){if(!v)return '—';const d=new Date(v);if(Number.isNaN(d.valueOf()))return t(v);return new Intl.DateTimeFormat('pt-PT',{day:'2-digit',month:'2-digit',year:'numeric'}).format(d);}
  function ageLabel(v){if(!v)return '';const d=new Date(v);if(Number.isNaN(d.valueOf()))return '';const h=Math.max(0,Math.round((Date.now()-d.valueOf())/36e5));if(h<24)return `há ${h}h`;const days=Math.round(h/24);return `há ${days}d`;}

  async function loadBase(){
    if(loading)return loading;
    loading=(async()=>{
      const r=await fetch(`./data/politicians.json?ts=${Date.now()}`,{cache:'no-store'});
      if(!r.ok)throw new Error(`Feed político HTTP ${r.status}`);
      const d=await r.json();
      if(!d||!Array.isArray(d.trades)||!Array.isArray(d.members))throw new Error('Feed político inválido');
      recentTrades=d.trades.map(x=>({ticker:t(x?.ticker).toUpperCase(),representative:t(x?.member||x?.representative)||'Membro do Congresso',chamber:t(x?.chamber),type:t(x?.type).toLowerCase(),amount:t(x?.amount)||'—',transaction_date:t(x?.transaction_date),disclosure_date:t(x?.disclosure_date),asset:t(x?.asset),filing_url:t(x?.filing_url)})).filter(x=>x.ticker&&x.representative);
      memberDirectory=d.members.map(x=>({key:t(x?.key)||`congress:${t(x?.name).toLowerCase().replace(/[^a-z0-9]+/g,'-')}`,name:t(x?.name),chamber:t(x?.chamber),count:Number(x?.count||0)||0,buys:Number(x?.buys||0)||0,sells:Number(x?.sells||0)||0,last:t(x?.last)})).filter(x=>x.name);
      feedMeta=d;
      if(!selected&&memberDirectory.length)selected=memberDirectory[0].key;
      return true;
    })().finally(()=>{loading=null;});
    return loading;
  }

  function rowsForMember(m){return recentTrades.filter(x=>x.representative===m.name);}
  function tickerButton(x){const link=x.filing_url?`<a class="politician-filing" href="${esc(x.filing_url)}" target="_blank" rel="noopener" title="Abrir filing">↗</a>`:'';return `<div class="politician-trade-wrap"><button type="button" class="politician-trade" data-market-ticker="${esc(x.ticker)}"><span><strong>${esc(x.ticker)}</strong><small>${esc(x.asset||'')} ${x.transaction_date?'· '+esc(shortDate(x.transaction_date)):''}</small></span><em class="${isBuy(x)?'is-buy':isSell(x)?'is-sell':''}">${isBuy(x)?'Compra':isSell(x)?'Venda':esc(x.type||'Trade')} · ${esc(x.amount||'—')}</em></button>${link}</div>`;}
  function bars(rows,side){const arr=rows.filter(side==='buy'?isBuy:isSell).sort((a,b)=>amountValue(b.amount)-amountValue(a.amount)).slice(0,10);const max=Math.max(1,...arr.map(x=>amountValue(x.amount)));if(!arr.length)return '<p class="politician-empty">Sem operações deste tipo na janela disponível.</p>';return arr.map(x=>`<button type="button" class="politician-bar" data-market-ticker="${esc(x.ticker)}"><span><strong>${esc(x.ticker)}</strong><small>${esc(shortDate(x.transaction_date))}</small></span><i><b style="width:${Math.max(7,amountValue(x.amount)/max*100)}%"></b></i><em>${esc(shortMoney(x.amount))}</em></button>`).join('');}
  function selectorHTML(){return `<select data-politician-select>${memberDirectory.map(x=>`<option value="${esc(x.key)}" ${selected===x.key?'selected':''}>${esc(x.name)}${x.chamber?` · ${esc(x.chamber)}`:''}${x.count?` · ${x.count} trades`:''}</option>`).join('')}</select>`;}

  async function render(){
    const root=document.getElementById('marketPrimary'); if(!root)return;
    const m=memberDirectory.find(x=>x.key===selected)||memberDirectory[0];
    if(!m){root.innerHTML='<div class="market-empty">Sem membros disponíveis no snapshot actual.</div>';return;}
    selected=m.key;
    const rows=rowsForMember(m),buys=rows.filter(isBuy).length,sells=rows.filter(isSell).length;
    const latest=rows.map(x=>x.disclosure_date||x.transaction_date).filter(Boolean).sort().reverse()[0]||m.last;
    const generated=feedMeta.generated_at||feedMeta.source_last_updated||'';
    root.innerHTML=`<section class="market-section politicians-section"><div class="market-section__head"><div><h3>Políticos</h3><p>Divulgações STOCK Act do Congresso dos EUA · House + Senate.</p></div><span class="market-data-age">${generated?esc(ageLabel(generated)):''}</span></div><div class="politician-picker"><label><span>Membro do Congresso</span>${selectorHTML()}</label></div><div id="politicianProfile"><div class="politician-profile"><div><small>${esc(m.chamber||'Congresso dos EUA')}</small><h3>${esc(m.name)}</h3><p>Transações publicamente divulgadas. Os valores são intervalos reportados e podem ser divulgados até 45 dias após a operação.</p></div><div class="politician-kpis"><span><small>Trades na janela</small><strong>${rows.length}</strong></span><span><small>Compras</small><strong class="is-buy">${buys}</strong></span><span><small>Vendas</small><strong class="is-sell">${sells}</strong></span><span><small>Último filing</small><strong>${esc(shortDate(latest))}</strong></span></div></div><div class="politician-sides"><section><div class="politician-side-head is-buy">↗ MAIORES COMPRAS <small>janela ${Number(feedMeta.window_days||92)}d</small></div>${bars(rows,'buy')}</section><section><div class="politician-side-head is-sell">↘ MAIORES VENDAS <small>janela ${Number(feedMeta.window_days||92)}d</small></div>${bars(rows,'sell')}</section></div><div class="market-detail-card politician-all"><div class="market-perspective-head"><div><small>ATIVIDADE RECENTE</small><h4>Operações divulgadas</h4></div><span class="market-data-age">${rows.length}</span></div>${rows.slice(0,100).map(tickerButton).join('')||'<p>Sem operações recentes para este membro.</p>'}</div><p class="market-source-credit">Fonte Vestra: ${esc(feedMeta.source||'feed STOCK Act')} · origem: ${esc(feedMeta.source_origin||'House Clerk + Senate eFD')}. Dados contextuais; não entram no score fundamental.</p></div></section>`;
  }

  async function openPoliticians(){const root=document.getElementById('marketPrimary');if(!root)return;document.querySelectorAll('.market-mode').forEach(x=>x.classList.remove('is-active'));document.querySelector('[data-politicians-mode]')?.classList.add('is-active');root.innerHTML='<div class="market-loader"><span></span><div>A carregar divulgações políticas…</div></div>';try{await loadBase();await render();}catch(e){root.innerHTML=`<div class="market-empty market-empty--error"><strong>Dados políticos indisponíveis</strong><br><span>${esc(e?.message||'Não foi possível carregar o snapshot Vestra.')}</span></div>`;}}
  function installButton(){const grid=document.querySelector('.market-mode-grid');if(!grid||grid.querySelector('[data-politicians-mode]'))return;const btn=document.createElement('button');btn.className='market-mode';btn.type='button';btn.dataset.politiciansMode='1';btn.innerHTML='<span class="market-mode__icon">♜</span><strong>Políticos</strong>';const smart=grid.querySelector('[data-market-mode="smart"]');smart?.insertAdjacentElement('afterend',btn)||grid.appendChild(btn);}
  function addStyle(){if(document.getElementById('vestra-politicians-style-v20'))return;const s=document.createElement('style');s.id='vestra-politicians-style-v20';s.textContent=`.politician-picker{margin:12px 0 16px}.politician-picker label{display:grid;gap:6px}.politician-picker label>span{font-size:11px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--text2)}.politician-picker select{width:100%;padding:12px 14px;border:1px solid var(--line);border-radius:14px;background:var(--card);color:var(--text);font:inherit}.politician-profile{display:grid;gap:14px;padding:18px;border:1px solid var(--line);border-radius:20px;background:var(--card);margin-bottom:14px}.politician-profile h3{margin:3px 0 4px}.politician-profile p{margin:0;color:var(--text2);font-size:12px}.politician-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.politician-kpis span{padding:10px;border-radius:12px;background:var(--soft);display:grid;gap:3px}.politician-kpis small{font-size:10px;color:var(--text2)}.politician-kpis strong{font-size:15px}.is-buy{color:#168f73!important}.is-sell{color:#c34f65!important}.politician-sides{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px}.politician-sides section{padding:14px;border:1px solid var(--line);border-radius:18px;background:var(--card)}.politician-side-head{font-size:11px;font-weight:900;letter-spacing:.05em;margin-bottom:10px}.politician-bar{width:100%;display:grid;grid-template-columns:minmax(72px,1fr) minmax(80px,2fr) auto;gap:8px;align-items:center;background:none;border:0;padding:7px 0;color:var(--text);text-align:left}.politician-bar span{display:grid}.politician-bar small{color:var(--text2);font-size:9px}.politician-bar i{height:4px;border-radius:8px;background:var(--soft);overflow:hidden}.politician-bar b{display:block;height:100%;background:currentColor;border-radius:8px}.politician-bar em{font-style:normal;font-size:11px;font-weight:700}.politician-trade-wrap{display:flex;align-items:center;border-bottom:1px solid var(--line)}.politician-trade{flex:1;display:flex;justify-content:space-between;gap:12px;padding:11px 0;border:0;background:none;color:var(--text);text-align:left}.politician-trade span{display:grid}.politician-trade small{color:var(--text2);font-size:10px}.politician-trade em{font-style:normal;font-size:11px;text-align:right}.politician-filing{padding:10px;text-decoration:none;color:var(--text2)}.politician-empty{font-size:11px;color:var(--text2)}@media(max-width:620px){.politician-sides{grid-template-columns:1fr}.politician-kpis{grid-template-columns:1fr 1fr}.politician-bar{grid-template-columns:74px 1fr auto}}`;document.head.appendChild(s);}
  document.addEventListener('click',e=>{const b=e.target.closest?.('[data-politicians-mode]');if(!b)return;e.preventDefault();e.stopPropagation();openPoliticians();});
  document.addEventListener('change',async e=>{if(!e.target.matches?.('[data-politician-select]'))return;selected=e.target.value;await render();});
  function start(){addStyle();installButton();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;installButton();});});mo.observe(document.body,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();