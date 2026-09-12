/* Vestra Politicians v2.1 — Congress + Executive disclosures, leaders and favourites. */
(() => {
  'use strict';
  const VERSION='2.1';
  const FAV_KEY='vestra-politician-favourites-v2';
  const t=v=>String(v??'').trim();
  const esc=v=>t(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let recentTrades=[];
  let memberDirectory=[];
  let selected='all';
  let view='all';
  let feedMeta={};
  let executiveMeta={};
  let loading=null;

  const isBuy=x=>/purchase|buy|compr/.test(t(x?.type).toLowerCase());
  const isSell=x=>/sale|sell|vend/.test(t(x?.type).toLowerCase());
  function amountValue(v){const s=t(v).replace(/,/g,'');const nums=[...s.matchAll(/\$?([0-9]+(?:\.[0-9]+)?)([KMB])?/gi)].map(m=>{let n=Number(m[1]);const u=t(m[2]).toUpperCase();if(u==='K')n*=1e3;if(u==='M')n*=1e6;if(u==='B')n*=1e9;return n;});return nums.length?nums.reduce((a,b)=>a+b,0)/nums.length:0;}
  function shortMoney(v){const n=amountValue(v);return n?new Intl.NumberFormat('pt-PT',{notation:'compact',maximumFractionDigits:1,style:'currency',currency:'USD'}).format(n):(t(v)||'—');}
  function shortDate(v){if(!v)return '—';const d=new Date(v);if(Number.isNaN(d.valueOf()))return t(v);return new Intl.DateTimeFormat('pt-PT',{day:'2-digit',month:'2-digit',year:'numeric'}).format(d);}
  function ageLabel(v){if(!v)return '';const d=new Date(v);if(Number.isNaN(d.valueOf()))return '';const h=Math.max(0,Math.round((Date.now()-d.valueOf())/36e5));if(h<24)return `há ${h}h`;const days=Math.round(h/24);return `há ${days}d`;}
  function favs(){try{return new Set(JSON.parse(localStorage.getItem(FAV_KEY)||'[]'))}catch{return new Set()}}
  function saveFavs(set){try{localStorage.setItem(FAV_KEY,JSON.stringify([...set]))}catch{}}
  function toggleFavourite(key){if(!key||key==='all')return;const f=favs();f.has(key)?f.delete(key):f.add(key);saveFavs(f);render();}

  function normalizeTrade(x,source='Congress'){
    return {ticker:t(x?.ticker).toUpperCase(),representative:t(x?.member||x?.representative)||'Responsável público',member_key:t(x?.member_key),chamber:t(x?.chamber)||source,type:t(x?.type).toLowerCase(),amount:t(x?.amount)||'—',transaction_date:t(x?.transaction_date),disclosure_date:t(x?.disclosure_date),asset:t(x?.asset),filing_url:t(x?.filing_url),source};
  }
  function memberKey(name,chamber){return `${t(chamber).toLowerCase()==='executive'?'executive':'congress'}:${t(name).toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')}`;}
  function buildMember(x,source='Congress'){
    const name=t(x?.name);const chamber=t(x?.chamber)||source;return {key:t(x?.key)||memberKey(name,chamber),name,chamber,role:t(x?.role),count:Number(x?.count||0)||0,buys:Number(x?.buys||0)||0,sells:Number(x?.sells||0)||0,last:t(x?.last),source_label:t(x?.source_label),source_url:t(x?.source_url)};
  }
  function politiciansSnapshotFresh(d){
    if(!d||Number(d.schema_version||0)<2||!Array.isArray(d.trades)||!Array.isArray(d.members))return false;
    const newest=t(d.newest_disclosure||d.source_last_updated).slice(0,10);const ms=newest?new Date(`${newest}T00:00:00Z`).valueOf():NaN;
    return Number.isFinite(ms)&&(Date.now()-ms)<=60*86400000;
  }
  function enrichMemberCounts(){
    const byName=new Map(memberDirectory.map(m=>[m.name,m]));
    for(const m of memberDirectory){const rows=recentTrades.filter(x=>x.representative===m.name);m.count=rows.length;m.buys=rows.filter(isBuy).length;m.sells=rows.filter(isSell).length;m.last=rows.map(x=>x.disclosure_date||x.transaction_date).filter(Boolean).sort().reverse()[0]||m.last;}
    for(const tr of recentTrades){if(byName.has(tr.representative))continue;const m=buildMember({name:tr.representative,chamber:tr.chamber},tr.source);memberDirectory.push(m);byName.set(m.name,m);}
    memberDirectory.sort((a,b)=>a.chamber==='Executive'?-1:b.chamber==='Executive'?1:(b.count-a.count)||a.name.localeCompare(b.name));
  }

  async function loadBase(){
    if(loading)return loading;
    loading=(async()=>{
      const r=await fetch(`./data/politicians.json?ts=${Date.now()}`,{cache:'no-store'});
      if(!r.ok)throw new Error(`Feed político HTTP ${r.status}`);
      const d=await r.json();
      if(!politiciansSnapshotFresh(d))throw new Error('Feed político inválido ou desactualizado');
      recentTrades=d.trades.map(x=>normalizeTrade(x,'Congress')).filter(x=>x.ticker&&x.representative);
      memberDirectory=d.members.map(x=>buildMember(x,'Congress')).filter(x=>x.name);
      feedMeta=d;

      try{
        const er=await fetch(`./data/executives.json?ts=${Date.now()}`,{cache:'no-store'});
        if(er.ok){
          const ed=await er.json();executiveMeta=ed||{};
          const execTrades=(ed?.trades||[]).map(x=>normalizeTrade(x,'Executive')).filter(x=>x.ticker&&x.representative);
          const execPeople=(ed?.people||[]).map(x=>buildMember(x,'Executive')).filter(x=>x.name);
          recentTrades.push(...execTrades);memberDirectory.push(...execPeople);
        }
      }catch(_){}
      enrichMemberCounts();
      return true;
    })().finally(()=>{loading=null;});
    return loading;
  }

  function rowsForMember(m){return recentTrades.filter(x=>x.representative===m.name);}
  function sortTrades(rows,side){return rows.filter(side==='buy'?isBuy:isSell).slice().sort((a,b)=>amountValue(b.amount)-amountValue(a.amount)||String(b.disclosure_date||b.transaction_date).localeCompare(String(a.disclosure_date||a.transaction_date)));}
  function tickerButton(x){const link=x.filing_url?`<a class="politician-filing" href="${esc(x.filing_url)}" target="_blank" rel="noopener" title="Abrir filing oficial">↗</a>`:'';return `<div class="politician-trade-wrap"><button type="button" class="politician-trade" data-market-ticker="${esc(x.ticker)}"><span><strong>${esc(x.ticker)}</strong><small>${esc(x.asset||'')} ${x.transaction_date?'· '+esc(shortDate(x.transaction_date)):''}</small></span><em class="${isBuy(x)?'is-buy':isSell(x)?'is-sell':''}">${isBuy(x)?'Compra':isSell(x)?'Venda':esc(x.type||'Trade')} · ${esc(x.amount||'—')}</em></button>${link}</div>`;}
  function bars(rows,side){const arr=sortTrades(rows,side).slice(0,10);const max=Math.max(1,...arr.map(x=>amountValue(x.amount)));if(!arr.length)return '<p class="politician-empty">Sem operações deste tipo na janela disponível.</p>';return arr.map((x,i)=>`<button type="button" class="politician-bar" data-market-ticker="${esc(x.ticker)}"><span class="politician-rank">${i+1}</span><span><strong>${esc(x.ticker)}</strong><small>${esc(x.representative)} · ${esc(shortDate(x.transaction_date))}</small></span><i><b style="width:${Math.max(7,amountValue(x.amount)/max*100)}%"></b></i><em>${esc(shortMoney(x.amount))}</em></button>`).join('');}
  function topSides(rows,title='Maiores movimentos'){return `<div class="politician-sides"><section><div class="politician-side-head is-buy">↗ TOP 10 COMPRAS <small>${esc(title)}</small></div>${bars(rows,'buy')}</section><section><div class="politician-side-head is-sell">↘ TOP 10 VENDAS <small>${esc(title)}</small></div>${bars(rows,'sell')}</section></div>`;}
  function selectorHTML(){
    const f=favs();const executives=memberDirectory.filter(x=>x.chamber==='Executive');const congress=memberDirectory.filter(x=>x.chamber!=='Executive');
    const opts=arr=>arr.map(x=>`<option value="${esc(x.key)}" ${selected===x.key?'selected':''}>${f.has(x.key)?'★ ':''}${esc(x.name)}${x.chamber?` · ${esc(x.chamber)}`:''}${x.count?` · ${x.count} trades`:''}</option>`).join('');
    return `<select data-politician-select><option value="all" ${selected==='all'?'selected':''}>Todos · ranking global</option>${executives.length?`<optgroup label="Executivo">${opts(executives)}</optgroup>`:''}<optgroup label="Congresso">${opts(congress)}</optgroup></select>`;
  }
  function favouriteCards(){
    const f=favs();const members=memberDirectory.filter(m=>f.has(m.key));
    if(!members.length)return '<div class="market-empty"><strong>Ainda não tens favoritos.</strong><br><span>Abre um político e toca em ☆ para o guardar aqui.</span></div>';
    return `<div class="politician-favourite-grid">${members.map(m=>`<button type="button" data-politician-open="${esc(m.key)}"><span>${m.chamber==='Executive'?'★':'☆'}</span><div><strong>${esc(m.name)}</strong><small>${esc(m.role||m.chamber)} · ${m.count} trades · ${m.buys} compras / ${m.sells} vendas</small></div><b>→</b></button>`).join('')}</div>`;
  }
  function topMemberCards(){
    const active=memberDirectory.slice().sort((a,b)=>b.count-a.count).slice(0,8);
    return `<div class="politician-member-grid">${active.map(m=>`<button type="button" data-politician-open="${esc(m.key)}"><strong>${esc(m.name)}</strong><small>${esc(m.role||m.chamber)} · ${m.count} trades</small><span>${m.buys} ↗ · ${m.sells} ↘</span></button>`).join('')}</div>`;
  }
  function globalView(){
    const latest=recentTrades.map(x=>x.disclosure_date||x.transaction_date).filter(Boolean).sort().reverse()[0];
    return `<div class="politician-profile politician-global"><div><small>RADAR GLOBAL</small><h3>Principais operações políticas</h3><p>Ranking pelo valor médio do intervalo divulgado. Executivo e Congresso permanecem identificados pela respetiva fonte oficial.</p></div><div class="politician-kpis"><span><small>Pessoas</small><strong>${memberDirectory.length}</strong></span><span><small>Compras</small><strong class="is-buy">${recentTrades.filter(isBuy).length}</strong></span><span><small>Vendas</small><strong class="is-sell">${recentTrades.filter(isSell).length}</strong></span><span><small>Último filing</small><strong>${esc(shortDate(latest))}</strong></span></div></div>${topSides(recentTrades,'todos os políticos')}<div class="market-detail-card politician-all"><div class="market-perspective-head"><div><small>MAIS ATIVOS</small><h4>Escolher político</h4></div><span class="market-data-age">${memberDirectory.length}</span></div>${topMemberCards()}</div>`;
  }
  function memberView(m){
    const rows=rowsForMember(m),buys=rows.filter(isBuy).length,sells=rows.filter(isSell).length;const latest=rows.map(x=>x.disclosure_date||x.transaction_date).filter(Boolean).sort().reverse()[0]||m.last;const isFav=favs().has(m.key);
    const source=m.chamber==='Executive'?(m.source_label||executiveMeta.source||'OGE Form 278-T'):(feedMeta.source||'House Clerk + Senate eFD');
    return `<div class="politician-profile"><div><small>${esc(m.role||m.chamber||'Responsável público')}</small><h3>${esc(m.name)}</h3><p>${m.chamber==='Executive'?'Divulgações financeiras do Executivo.':'Transações publicamente divulgadas ao abrigo do STOCK Act.'} Os valores são intervalos reportados e não representam necessariamente decisões pessoais do titular.</p><button type="button" class="politician-favourite ${isFav?'is-active':''}" data-politician-favourite="${esc(m.key)}">${isFav?'★ Favorito':'☆ Adicionar aos favoritos'}</button></div><div class="politician-kpis"><span><small>Trades disponíveis</small><strong>${rows.length}</strong></span><span><small>Compras</small><strong class="is-buy">${buys}</strong></span><span><small>Vendas</small><strong class="is-sell">${sells}</strong></span><span><small>Último filing</small><strong>${esc(shortDate(latest))}</strong></span></div></div>${topSides(rows,m.name)}<div class="market-detail-card politician-all"><div class="market-perspective-head"><div><small>ATIVIDADE DISPONÍVEL</small><h4>Operações divulgadas</h4></div><span class="market-data-age">${rows.length}</span></div>${rows.slice().sort((a,b)=>String(b.disclosure_date||b.transaction_date).localeCompare(String(a.disclosure_date||a.transaction_date))).slice(0,100).map(tickerButton).join('')||'<p>Sem operações recentes para esta pessoa.</p>'}</div><p class="market-source-credit">Fonte: ${esc(source)} · dados contextuais; não entram no Score Vestra.</p>`;
  }

  async function render(){
    const root=document.getElementById('marketPrimary');if(!root)return;
    const generated=feedMeta.generated_at||feedMeta.source_last_updated||'';
    const coverage=[...(feedMeta.coverage_chambers||[]),'Executive'].filter((x,i,a)=>x&&a.indexOf(x)===i).join(' + ');
    let body='';
    if(view==='favourites')body=favouriteCards();
    else if(selected==='all')body=globalView();
    else {const m=memberDirectory.find(x=>x.key===selected);body=m?memberView(m):globalView();}
    root.innerHTML=`<section class="market-section politicians-section"><div class="market-section__head"><div><h3>Políticos</h3><p>Top 10 compras e vendas · Congresso + Executivo · ${esc(coverage)}.</p></div><span class="market-data-age">${generated?esc(ageLabel(generated)):''}</span></div><div class="politician-view-tabs"><button type="button" data-politician-view="all" class="${view==='all'?'is-active':''}">Todos</button><button type="button" data-politician-view="favourites" class="${view==='favourites'?'is-active':''}">★ Favoritos <span>${favs().size}</span></button></div><div class="politician-picker"><label><span>Escolher político</span>${selectorHTML()}</label></div><div id="politicianProfile">${body}</div><p class="market-source-credit">Congresso: House Clerk + Senate eFD · Executivo: OGE/White House. Rankings usam o ponto médio do intervalo divulgado; não são recomendações de investimento.</p></section>`;
  }

  async function openPoliticians(){const root=document.getElementById('marketPrimary');if(!root)return;document.querySelectorAll('.market-mode').forEach(x=>x.classList.remove('is-active'));document.querySelector('[data-politicians-mode]')?.classList.add('is-active');root.innerHTML='<div class="market-loader"><span></span><div>A carregar divulgações políticas…</div></div>';try{await loadBase();await render();}catch(e){root.innerHTML=`<div class="market-empty market-empty--error"><strong>Dados políticos indisponíveis</strong><br><span>${esc(e?.message||'Não foi possível carregar o snapshot Vestra.')}</span></div>`;}}
  function installButton(){const grid=document.querySelector('.market-mode-grid');if(!grid||grid.querySelector('[data-politicians-mode]'))return;const btn=document.createElement('button');btn.className='market-mode';btn.type='button';btn.dataset.politiciansMode='1';btn.innerHTML='<span class="market-mode__icon">♜</span><strong>Políticos</strong>';const smart=grid.querySelector('[data-market-mode="smart"]');smart?.insertAdjacentElement('afterend',btn)||grid.appendChild(btn);}
  function addStyle(){if(document.getElementById('vestra-politicians-style-v21'))return;const link=document.createElement('link');link.id='vestra-politicians-style-v21';link.rel='stylesheet';link.href='politicians.css?v=1.0';document.head.appendChild(link);}
  document.addEventListener('click',e=>{const b=e.target.closest?.('[data-politicians-mode]');if(b){e.preventDefault();e.stopPropagation();openPoliticians();return;}const fav=e.target.closest?.('[data-politician-favourite]');if(fav){e.preventDefault();toggleFavourite(fav.dataset.politicianFavourite);return;}const v=e.target.closest?.('[data-politician-view]');if(v){e.preventDefault();view=v.dataset.politicianView||'all';render();return;}const open=e.target.closest?.('[data-politician-open]');if(open){e.preventDefault();selected=open.dataset.politicianOpen||'all';view='all';render();return;}});
  document.addEventListener('change',async e=>{if(!e.target.matches?.('[data-politician-select]'))return;selected=e.target.value||'all';view='all';await render();});
  function start(){addStyle();installButton();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;installButton();});});mo.observe(document.body,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();