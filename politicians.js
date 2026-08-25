/* Vestra Politicians v1.2 — Congress directory + Executive Branch disclosures. */
(() => {
  'use strict';
  const VERSION='1.2';
  const t=v=>String(v??'').trim();
  const esc=v=>t(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let recentTrades=[];
  let memberDirectory=[];
  let memberTrades=new Map();
  let selected='executive:donald-trump';
  let loading=null;

  const EXECUTIVES=[{
    key:'executive:donald-trump',name:'Donald J. Trump',role:'President of the United States',group:'Executive Branch',party:'Republican',
    filingDate:'2026-08-22',period:'June 2026',tradeCountText:'1,000+',buyCountText:'550+',sellCountText:'450+',
    note:'Atividade declarada em OGE Form 278-T. As contas são reportadas como geridas por terceiros; os valores são intervalos, não montantes exatos.',
    sourceUrl:'https://extapps2.oge.gov/201/Presiden.nsf',
    highlights:[
      {ticker:'BRK-B',type:'purchase',amount:'$1,000,001 - $5,000,000',date:'2026-06-18',asset:'Berkshire Hathaway'},
      {ticker:'V',type:'purchase',amount:'≥ $1,000,000',date:'2026-06-18',asset:'Visa'},
      {ticker:'MA',type:'purchase',amount:'≥ $1,000,000',date:'2026-06-18',asset:'Mastercard'},
      {ticker:'CTAS',type:'purchase',amount:'significant purchase',date:'2026-06-18',asset:'Cintas'},
      {ticker:'META',type:'sale',amount:'$1,000,001 - $5,000,000',date:'2026-06-18',asset:'Meta Platforms'},
      {ticker:'PLTR',type:'purchase',amount:'$1,001 - $15,000',date:'2026-06-03',asset:'Palantir'},
      {ticker:'PLTR',type:'sale',amount:'$15,001 - $50,000',date:'2026-06-16',asset:'Palantir'},
      {ticker:'PLTR',type:'sale',amount:'$500,001 - $1,000,000',date:'2026-06-18',asset:'Palantir'},
      {ticker:'PLTR',type:'purchase',amount:'purchase disclosed',date:'2026-06-23',asset:'Palantir'},
      {ticker:'HD',type:'purchase',amount:'purchase disclosed',date:'2026-06-18',asset:'Home Depot'}
    ]
  }];

  function normalizeTrade(x){
    return {
      ticker:t(x?.ticker).toUpperCase(), representative:t(x?.representative||x?.member||x?.name)||'Membro do Congresso',
      member_slug:t(x?.member_slug||x?.slug), chamber:t(x?.chamber), state:t(x?.state), party:t(x?.party),
      type:t(x?.type||x?.transaction||x?.transaction_type).toLowerCase(), amount:t(x?.amount||x?.amount_range)||'—',
      transaction_date:t(x?.transaction_date||x?.date), disclosure_date:t(x?.disclosure_date||x?.filed_date||x?.filing_date),
      owner:t(x?.owner||x?.asset_owner), asset:t(x?.asset||x?.security||''), source:'Bargo / STOCK Act'
    };
  }
  function normalizeMember(x){
    const name=t(x?.member||x?.name||x?.representative);
    const slug=t(x?.member_slug||x?.slug)||name.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
    return {key:`congress:${slug}`,slug,name,chamber:t(x?.chamber),state:t(x?.state),party:t(x?.party),count:Number(x?.trade_count||x?.trades||x?.count||0)||0,buys:Number(x?.buys||x?.buy_count||0)||0,sells:Number(x?.sells||x?.sell_count||0)||0,last:t(x?.last_trade_date||x?.last_trade||x?.latest_date)};
  }
  const isBuy=x=>/purchase|buy|compr/.test(t(x?.type).toLowerCase());
  const isSell=x=>/sale|sell|vend/.test(t(x?.type).toLowerCase());
  function amountValue(v){const s=t(v).replace(/,/g,'');const nums=[...s.matchAll(/\$?([0-9]+(?:\.[0-9]+)?)([KMB])?/gi)].map(m=>{let n=Number(m[1]);const u=t(m[2]).toUpperCase();if(u==='K')n*=1e3;if(u==='M')n*=1e6;if(u==='B')n*=1e9;return n;});return nums.length?nums.reduce((a,b)=>a+b,0)/nums.length:0;}
  function shortMoney(v){const n=amountValue(v);return n?new Intl.NumberFormat('pt-PT',{notation:'compact',maximumFractionDigits:1,style:'currency',currency:'USD'}).format(n):(t(v)||'—');}
  function shortDate(v){if(!v)return '—';const d=new Date(v);if(Number.isNaN(d.valueOf()))return t(v);return new Intl.DateTimeFormat('pt-PT',{day:'2-digit',month:'2-digit',year:'numeric'}).format(d);}

  async function fetchJson(url){const r=await fetch(url,{cache:'no-store',mode:'cors'});if(!r.ok)throw new Error(`HTTP ${r.status}`);return r.json();}
  async function loadBase(){
    if(loading)return loading;
    loading=(async()=>{
      const base='https://www.bargo.ai/free-apis/congress/v1';
      const [membersResult,tradesResult]=await Promise.allSettled([fetchJson(`${base}/members`),fetchJson(`${base}/trades?limit=100&page=0`)]);
      if(membersResult.status==='fulfilled'){
        const d=membersResult.value; const arr=Array.isArray(d)?d:(d?.members||d?.data||[]);
        memberDirectory=arr.map(normalizeMember).filter(x=>x.name).sort((a,b)=>b.count-a.count||a.name.localeCompare(b.name));
      }
      if(tradesResult.status==='fulfilled'){
        const d=tradesResult.value; const arr=Array.isArray(d)?d:(d?.trades||d?.data||[]);
        recentTrades=arr.map(normalizeTrade).filter(x=>x.ticker&&x.representative);
      }
      if(!memberDirectory.length){
        const m=new Map(); recentTrades.forEach(x=>{const k=x.representative;const p=m.get(k)||normalizeMember({name:k,member_slug:x.member_slug,chamber:x.chamber,state:x.state,party:x.party});p.count++;if(isBuy(x))p.buys++;if(isSell(x))p.sells++;m.set(k,p);}); memberDirectory=[...m.values()];
      }
      return true;
    })().finally(()=>{loading=null;});
    return loading;
  }

  async function loadCongressMember(m){
    if(memberTrades.has(m.key))return memberTrades.get(m.key);
    const base='https://www.bargo.ai/free-apis/congress/v1';
    let rows=[];
    try{
      const d=await fetchJson(`${base}/members/${encodeURIComponent(m.slug)}`);
      const arr=Array.isArray(d)?d:(d?.trades||d?.data?.trades||d?.data||[]);
      rows=arr.map(normalizeTrade).filter(x=>x.ticker);
    }catch(_){
      rows=recentTrades.filter(x=>x.representative===m.name);
    }
    memberTrades.set(m.key,rows); return rows;
  }

  function tickerButton(x){return `<button type="button" class="politician-trade" data-market-ticker="${esc(x.ticker)}"><span><strong>${esc(x.ticker)}</strong><small>${esc(x.asset||'')} ${x.transaction_date?'· '+esc(shortDate(x.transaction_date)):''}</small></span><em class="${isBuy(x)?'is-buy':isSell(x)?'is-sell':''}">${isBuy(x)?'Compra':isSell(x)?'Venda':esc(x.type||'Trade')} · ${esc(x.amount||'—')}</em></button>`;}
  function bars(rows,side){
    const arr=rows.filter(side==='buy'?isBuy:isSell).sort((a,b)=>amountValue(b.amount)-amountValue(a.amount)).slice(0,10); const max=Math.max(1,...arr.map(x=>amountValue(x.amount)));
    if(!arr.length)return '<p class="politician-empty">Sem operações deste tipo no período disponível.</p>';
    return arr.map(x=>`<button type="button" class="politician-bar" data-market-ticker="${esc(x.ticker)}"><span><strong>${esc(x.ticker)}</strong><small>${esc(shortDate(x.transaction_date))}</small></span><i><b style="width:${Math.max(7,amountValue(x.amount)/max*100)}%"></b></i><em>${esc(shortMoney(x.amount))}</em></button>`).join('');
  }
  function selectorHTML(){
    return `<select data-politician-select><optgroup label="Executive Branch">${EXECUTIVES.map(x=>`<option value="${esc(x.key)}" ${selected===x.key?'selected':''}>${esc(x.name)} · ${esc(x.role)}</option>`).join('')}</optgroup><optgroup label="Congresso — ${memberDirectory.length} membros">${memberDirectory.map(x=>`<option value="${esc(x.key)}" ${selected===x.key?'selected':''}>${esc(x.name)}${x.count?` · ${x.count} trades`:''}</option>`).join('')}</optgroup></select>`;
  }
  async function render(){
    const root=document.getElementById('marketPrimary'); if(!root)return;
    root.innerHTML=`<section class="market-section politicians-section"><div class="market-section__head"><div><h3>Políticos</h3><p>Congresso + Executive Branch · divulgações financeiras públicas.</p></div><span class="market-data-age">${memberDirectory.length}+ perfis</span></div><div class="politician-picker"><label><span>Político</span>${selectorHTML()}</label></div><div id="politicianProfile"><div class="market-loader"><span></span><div>A carregar perfil…</div></div></div></section>`;
    const host=document.getElementById('politicianProfile');
    const executive=EXECUTIVES.find(x=>x.key===selected);
    if(executive){
      const rows=executive.highlights.map(x=>({...x,representative:executive.name,source:'US OGE'}));
      host.innerHTML=`<div class="politician-profile"><div><small>${esc(executive.role)} · ${esc(executive.party)} · Executive Branch</small><h3>${esc(executive.name)}</h3><p>${esc(executive.note)}</p></div><div class="politician-kpis"><span><small>Trades no filing</small><strong>${esc(executive.tradeCountText)}</strong></span><span><small>Compras</small><strong class="is-buy">${esc(executive.buyCountText)}</strong></span><span><small>Vendas</small><strong class="is-sell">${esc(executive.sellCountText)}</strong></span><span><small>Filing</small><strong>${esc(shortDate(executive.filingDate))}</strong></span></div></div><div class="politician-callout"><strong>Última divulgação destacada · ${esc(executive.period)}</strong><span>O filing reporta mais de 1.000 transações. Abaixo estão operações destacadas do documento/reporting público, não a totalidade das linhas.</span></div><div class="politician-sides"><section><div class="politician-side-head is-buy">↗ COMPRAS DESTACADAS</div>${bars(rows,'buy')}</section><section><div class="politician-side-head is-sell">↘ VENDAS DESTACADAS</div>${bars(rows,'sell')}</section></div><div class="market-detail-card politician-all"><div class="market-perspective-head"><div><small>DESTAQUES DO FILING</small><h4>Operações identificadas</h4></div><span class="market-data-age">${rows.length}</span></div>${rows.map(tickerButton).join('')}</div><p class="market-source-credit">Fonte primária: U.S. Office of Government Ethics, OGE Form 278-T. A lista acima é um resumo dos destaques públicos do filing e não deve ser interpretada como o ficheiro bruto completo.</p>`;
      return;
    }
    const m=memberDirectory.find(x=>x.key===selected)||memberDirectory[0]; if(!m){host.innerHTML='<div class="market-empty">Sem membros disponíveis.</div>';return;}
    const rows=await loadCongressMember(m); const buys=rows.filter(isBuy).length,sells=rows.filter(isSell).length; const latest=rows.map(x=>x.disclosure_date||x.transaction_date).filter(Boolean).sort().reverse()[0]||m.last;
    host.innerHTML=`<div class="politician-profile"><div><small>${esc([m.chamber,m.party,m.state].filter(Boolean).join(' · ')||'Congresso dos EUA')}</small><h3>${esc(m.name)}</h3><p>Perfil carregado individualmente a partir das divulgações STOCK Act disponíveis.</p></div><div class="politician-kpis"><span><small>Trades conhecidos</small><strong>${m.count||rows.length}</strong></span><span><small>Compras recentes</small><strong class="is-buy">${buys}</strong></span><span><small>Vendas recentes</small><strong class="is-sell">${sells}</strong></span><span><small>Último filing</small><strong>${esc(shortDate(latest))}</strong></span></div></div><div class="politician-sides"><section><div class="politician-side-head is-buy">↗ MAIORES COMPRAS <small>período disponível</small></div>${bars(rows,'buy')}</section><section><div class="politician-side-head is-sell">↘ MAIORES VENDAS <small>período disponível</small></div>${bars(rows,'sell')}</section></div><div class="market-detail-card politician-all"><div class="market-perspective-head"><div><small>ATIVIDADE RECENTE</small><h4>Operações carregadas</h4></div><span class="market-data-age">${rows.length}</span></div>${rows.slice(0,100).map(tickerButton).join('')||'<p>Sem operações recentes no feed gratuito.</p>'}</div><p class="market-source-credit">Fonte: Bargo, com origem em divulgações oficiais STOCK Act da House e Senate. O diretório inclui o universo de membros disponibilizado pela fonte; o feed gratuito de operações é uma janela recente.</p>`;
  }

  async function openPoliticians(){
    const root=document.getElementById('marketPrimary'); if(!root)return;
    document.querySelectorAll('.market-mode').forEach(x=>x.classList.remove('is-active'));document.querySelector('[data-politicians-mode]')?.classList.add('is-active');
    root.innerHTML='<div class="market-loader"><span></span><div>A carregar diretório político…</div></div>';
    try{await loadBase();await render();}catch(e){root.innerHTML=`<div class="market-empty market-empty--error"><strong>Dados políticos indisponíveis</strong><br><span>${esc(e?.message||'Não foi possível carregar os dados.')}</span></div>`;}
  }
  function installButton(){const grid=document.querySelector('.market-mode-grid');if(!grid||grid.querySelector('[data-politicians-mode]'))return;const btn=document.createElement('button');btn.className='market-mode';btn.type='button';btn.dataset.politiciansMode='1';btn.innerHTML='<span class="market-mode__icon">♜</span><strong>Políticos</strong>';const smart=grid.querySelector('[data-market-mode="smart"]');smart?.insertAdjacentElement('afterend',btn)||grid.appendChild(btn);}
  function addStyle(){if(document.getElementById('vestra-politicians-style-v12'))return;const s=document.createElement('style');s.id='vestra-politicians-style-v12';s.textContent=`.politician-picker{margin:12px 0 16px}.politician-picker label{display:grid;gap:6px}.politician-picker label>span{font-size:11px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--text2)}.politician-picker select{width:100%;padding:12px 14px;border:1px solid var(--line);border-radius:14px;background:var(--card);color:var(--text);font:inherit}.politician-profile{display:grid;gap:14px;padding:18px;border:1px solid var(--line);border-radius:20px;background:var(--card);margin-bottom:14px}.politician-profile h3{margin:3px 0 4px}.politician-profile p{margin:0;color:var(--text2);font-size:12px}.politician-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.politician-kpis span{padding:10px;border-radius:12px;background:var(--soft);display:grid;gap:3px}.politician-kpis small{font-size:10px;color:var(--text2)}.politician-kpis strong{font-size:15px}.is-buy{color:#168f73!important}.is-sell{color:#c34f65!important}.politician-callout{display:grid;gap:4px;padding:12px 14px;border-radius:14px;background:var(--soft);margin:-2px 0 14px}.politician-callout span{font-size:11px;color:var(--text2)}.politician-sides{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px}.politician-sides section{padding:14px;border:1px solid var(--line);border-radius:18px;background:var(--card)}.politician-side-head{font-size:11px;font-weight:900;letter-spacing:.05em;margin-bottom:10px}.politician-bar{width:100%;display:grid;grid-template-columns:minmax(72px,1fr) minmax(80px,2fr) auto;gap:8px;align-items:center;background:none;border:0;padding:7px 0;color:var(--text);text-align:left}.politician-bar span{display:grid}.politician-bar small{color:var(--text2);font-size:9px}.politician-bar i{height:4px;border-radius:8px;background:var(--soft);overflow:hidden}.politician-bar b{display:block;height:100%;background:currentColor;border-radius:8px}.politician-bar em{font-style:normal;font-size:11px;font-weight:700}.politician-trade{width:100%;display:flex;justify-content:space-between;gap:12px;padding:11px 0;border:0;border-bottom:1px solid var(--line);background:none;color:var(--text);text-align:left}.politician-trade span{display:grid}.politician-trade small{color:var(--text2);font-size:10px}.politician-trade em{font-style:normal;font-size:11px;text-align:right}.politician-empty{font-size:11px;color:var(--text2)}@media(max-width:620px){.politician-sides{grid-template-columns:1fr}.politician-kpis{grid-template-columns:1fr 1fr}.politician-bar{grid-template-columns:74px 1fr auto}}`;document.head.appendChild(s);}
  document.addEventListener('click',e=>{const b=e.target.closest?.('[data-politicians-mode]');if(!b)return;e.preventDefault();e.stopPropagation();openPoliticians();});
  document.addEventListener('change',async e=>{if(!e.target.matches?.('[data-politician-select]'))return;selected=e.target.value;await render();});
  function start(){addStyle();installButton();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;installButton();});});mo.observe(document.body,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();