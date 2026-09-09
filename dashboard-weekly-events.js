/* Vestra Dashboard Weekly Events v1.3 — tappable earnings + macro catalysts with result details. */
(() => {
  'use strict';

  const VERSION = '1.3';
  const CARD_ID = 'dashboardWeeklyEventsCard';
  const STYLE_ID = 'dashboardWeeklyEventsStyle';
  const DETAIL_ID = 'dashboardWeeklyEventDetail';
  const MAX_EVENTS = 12;
  const WINDOW_DAYS = 7;
  const MACRO_URL = 'data/macro-events.json';
  let macroSnapshot = null;
  let macroLoading = null;
  let lastRenderedEvents = [];

  const text = value => String(value ?? '').trim();
  const number = value => {
    if (value === null || value === undefined || value === '') return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  };
  const tickerKey = value => text(value).toUpperCase();
  const localDay = date => new Date(date.getFullYear(), date.getMonth(), date.getDate());

  function parseCalendarDate(value) {
    const raw = text(value);
    if (!raw) return null;
    const plain = /^(\d{4})-(\d{2})-(\d{2})/.exec(raw);
    if (plain) {
      const date = new Date(Number(plain[1]), Number(plain[2]) - 1, Number(plain[3]));
      return Number.isNaN(date.getTime()) ? null : date;
    }
    const date = new Date(raw);
    return Number.isNaN(date.getTime()) ? null : localDay(date);
  }

  function portfolioContext() {
    return window.VestraMarketPortfolioContext?.create({
      getAssets: () => {
        try { return (typeof state !== 'undefined' && state && Array.isArray(state.assets)) ? state.assets : []; }
        catch (_) { return []; }
      },
      text,
      number,
    }) || null;
  }

  function portfolioTickerSet(context = portfolioContext()) {
    try { return context?.portfolioTickers?.() || new Set(); }
    catch (_) { return new Set(); }
  }

  function tickerMatchesPortfolio(ticker, tickers) {
    const normalized = tickerKey(ticker);
    if (!normalized) return false;
    return [...(tickers || [])].some(value => tickerKey(value) === normalized);
  }

  function dateISO(date) {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  }

  function collectEvents(stocks, portfolioTickers = new Set(), now = new Date(), windowDays = WINDOW_DAYS) {
    const start = localDay(now);
    const end = new Date(start);
    end.setDate(end.getDate() + Math.max(1, Number(windowDays) || WINDOW_DAYS) - 1);
    const out = [];
    for (const stock of (Array.isArray(stocks) ? stocks : [])) {
      const ticker = tickerKey(stock?.ticker);
      const quoteType = tickerKey(stock?.quote_type);
      if (!ticker || ['ETF','FUND','MUTUALFUND','CRYPTO'].includes(quoteType)) continue;
      const common = {
        kind: 'earnings', ticker, name: text(stock?.name) || ticker,
        title: text(stock?.name) || ticker, marketCap: number(stock?.market_cap) || 0,
        inPortfolio: tickerMatchesPortfolio(ticker, portfolioTickers),
      };
      const latest = parseCalendarDate(stock?.analyst_latest_earnings_date);
      if (latest && latest >= start && latest <= end) {
        out.push({
          ...common, date: latest, dateISO: dateISO(latest), source: 'analyst_latest_earnings_date',
          reported: true,
          epsEstimate: number(stock?.analyst_latest_eps_estimate),
          epsActual: number(stock?.analyst_latest_eps_actual),
          epsSurprisePct: number(stock?.analyst_latest_eps_surprise_pct),
        });
      }
      const upcoming = parseCalendarDate(stock?.analyst_next_earnings_date);
      if (upcoming && upcoming >= start && upcoming <= end && (!latest || dateISO(latest) !== dateISO(upcoming))) {
        out.push({
          ...common, date: upcoming, dateISO: dateISO(upcoming), source: 'analyst_next_earnings_date',
          reported: false,
          epsEstimate: number(stock?.analyst_eps_next_q),
          epsActual: null,
          epsSurprisePct: null,
        });
      }
    }
    return out;
  }

  function collectMacroEvents(snapshot, now = new Date(), windowDays = WINDOW_DAYS) {
    const start = localDay(now);
    const end = new Date(start);
    end.setDate(end.getDate() + Math.max(1, Number(windowDays) || WINDOW_DAYS) - 1);
    const rows = Array.isArray(snapshot) ? snapshot : (snapshot?.events || []);
    return rows.map((row, index) => {
      const eventStart = parseCalendarDate(row?.date);
      const eventEnd = parseCalendarDate(row?.date_end || row?.date);
      if (!eventStart || !eventEnd || eventStart > end || eventEnd < start) return null;
      return {
        kind: 'macro',
        id: `${text(row?.source) || 'macro'}:${text(row?.date)}:${text(row?.short_title) || index}`,
        title: text(row?.title) || text(row?.short_title) || 'Evento macro',
        shortTitle: text(row?.short_title) || text(row?.title) || 'Macro',
        date: eventStart < start ? start : eventStart,
        dateEnd: eventEnd,
        region: text(row?.region), category: text(row?.category),
        importance: text(row?.importance) || 'high', timeLocal: text(row?.time_local),
        source: text(row?.source),
        actual: row?.actual ?? null,
        consensus: row?.consensus ?? row?.forecast ?? null,
        previous: row?.previous ?? null,
        unit: text(row?.unit), resultStatus: text(row?.result_status),
      };
    }).filter(Boolean);
  }

  function selectEvents(stocks, portfolioTickers = new Set(), now = new Date(), limit = MAX_EVENTS, macro = macroSnapshot) {
    const macroEvents = collectMacroEvents(macro, now);
    const earnings = collectEvents(stocks, portfolioTickers, now);
    const portfolioEarnings = earnings.filter(x => x.inPortfolio).sort((a,b)=>a.date-b.date || b.marketCap-a.marketCap);
    const marketEarnings = earnings.filter(x => !x.inPortfolio).sort((a,b)=>b.marketCap-a.marketCap || a.date-b.date);
    const cap = Math.max(1, Number(limit) || MAX_EVENTS);
    const selected = [];
    const push = event => { if (selected.length < cap) selected.push(event); };
    macroEvents.sort((a,b)=>a.date-b.date || (a.importance === 'critical' ? -1 : 1)).forEach(push);
    portfolioEarnings.forEach(push);
    marketEarnings.forEach(push);
    return selected.sort((a,b) => {
      if (a.date.getTime() !== b.date.getTime()) return a.date - b.date;
      if (a.kind !== b.kind) return a.kind === 'macro' ? -1 : 1;
      if (a.inPortfolio !== b.inPortfolio) return a.inPortfolio ? -1 : 1;
      return (b.marketCap || 0) - (a.marketCap || 0);
    });
  }

  function dayLabel(date, now = new Date()) {
    const today = localDay(now);
    const target = localDay(date);
    const diff = Math.round((target - today) / 86400000);
    if (diff === 0) return 'Hoje';
    if (diff === 1) return 'Amanhã';
    const weekday = new Intl.DateTimeFormat('pt-PT', { weekday: 'short' }).format(target).replace('.', '');
    const calendar = new Intl.DateTimeFormat('pt-PT', { day: 'numeric', month: 'short' }).format(target).replace('.', '');
    return `${weekday} · ${calendar}`;
  }

  function categoryLabel(event) {
    if (event.kind === 'earnings') return 'Resultados';
    if (event.category === 'central_bank') return 'Banco central';
    if (event.category === 'inflation') return 'Inflação';
    if (event.category === 'labour') return 'Emprego';
    if (event.category === 'growth') return 'Crescimento';
    if (event.category === 'activity') return 'Atividade';
    return 'Macro';
  }

  function sourceLabel(source) {
    return ({ fed:'Federal Reserve', bls:'U.S. BLS', bea:'U.S. BEA', ecb:'Banco Central Europeu', census:'U.S. Census' })[text(source)] || text(source) || 'Vestra';
  }

  function hasMacroResult(event) {
    return event?.actual !== null && event?.actual !== undefined && text(event.actual) !== '';
  }

  function formatResultValue(value, unit = '') {
    if (value === null || value === undefined || text(value) === '') return '—';
    return `${text(value)}${unit ? ` ${unit}` : ''}`;
  }

  function formatEPS(value) {
    const parsed = number(value);
    return parsed === null ? '—' : parsed.toLocaleString('pt-PT', { maximumFractionDigits: 4 });
  }

  function formatSurprise(value) {
    const parsed = number(value);
    if (parsed === null) return '—';
    return `${(parsed * 100).toLocaleString('pt-PT', { maximumFractionDigits: 1, minimumFractionDigits: 1 })}%`;
  }

  async function loadMacroEvents(fetchImpl = (...args) => fetch(...args)) {
    if (macroSnapshot) return macroSnapshot;
    if (macroLoading) return macroLoading;
    macroLoading = (async () => {
      try {
        const response = await fetchImpl(MACRO_URL, { cache: 'no-store' });
        if (!response.ok) return null;
        const payload = await response.json();
        if (!payload || !Array.isArray(payload.events)) return null;
        macroSnapshot = payload;
        return macroSnapshot;
      } catch (_) { return null; }
      finally { macroLoading = null; }
    })();
    return macroLoading;
  }

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
      .weekly-events-card{overflow:hidden}.weekly-events-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:12px}.weekly-events-kicker{font-size:10px;font-weight:800;letter-spacing:.55px;text-transform:uppercase;color:var(--muted,#64748b);margin-bottom:3px}.weekly-events-title{font-size:16px;font-weight:850;letter-spacing:-.2px;color:var(--text,#17212b)}.weekly-events-range{font-size:11px;color:var(--muted,#64748b);white-space:nowrap;padding-top:2px}
      .weekly-events-list{display:flex;gap:9px;overflow-x:auto;scroll-snap-type:x proximity;padding:1px 2px 5px;margin:0 -2px;-webkit-overflow-scrolling:touch;scrollbar-width:none}.weekly-events-list::-webkit-scrollbar{display:none}
      .weekly-event{appearance:none;border:1px solid var(--line,#e5e7eb);background:var(--card,#fff);border-radius:14px;padding:11px 12px;min-width:168px;max-width:220px;text-align:left;scroll-snap-align:start;color:inherit;box-shadow:0 1px 2px rgba(15,23,42,.025);cursor:pointer;position:relative}.weekly-event::after{content:'›';position:absolute;right:10px;top:9px;font-size:17px;line-height:1;color:var(--muted,#64748b);opacity:.55}.weekly-event:active{transform:scale(.985)}
      .weekly-event--portfolio{border-color:rgba(23,123,120,.35);background:linear-gradient(180deg,rgba(23,123,120,.07),rgba(23,123,120,.025))}.weekly-event--macro{border-color:rgba(99,102,241,.28);background:linear-gradient(180deg,rgba(99,102,241,.075),rgba(99,102,241,.025))}.weekly-event--critical{border-color:rgba(180,83,9,.35);background:linear-gradient(180deg,rgba(245,158,11,.09),rgba(245,158,11,.025))}
      .weekly-event__day{font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.35px;color:#177B78;margin-bottom:7px;padding-right:14px}.weekly-event__ticker{font-size:14px;font-weight:900;line-height:1.15;margin-bottom:4px}.weekly-event__name{font-size:11px;color:var(--muted,#64748b);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:9px}.weekly-event__meta{display:flex;align-items:center;gap:5px;flex-wrap:wrap;font-size:9px;font-weight:800}.weekly-event__type,.weekly-event__portfolio,.weekly-event__critical{padding:3px 6px;border-radius:999px}.weekly-event__type{background:rgba(99,102,241,.10);color:#5558b9}.weekly-event__portfolio{background:rgba(23,123,120,.12);color:#116b68}.weekly-event__critical{background:rgba(245,158,11,.14);color:#9a5b08}.weekly-events-empty{padding:12px 0 4px;color:var(--muted,#64748b);font-size:12px}.weekly-events-foot{margin-top:8px;font-size:9px;line-height:1.35;color:var(--muted,#64748b);opacity:.8}
      .weekly-detail-backdrop{position:fixed;inset:0;z-index:10050;background:rgba(12,22,31,.34);display:flex;align-items:flex-end;justify-content:center;padding:14px;backdrop-filter:blur(3px)}.weekly-detail-sheet{width:min(560px,100%);max-height:min(78vh,680px);overflow:auto;border-radius:24px 24px 18px 18px;background:var(--card,#fff);color:var(--text,#17212b);box-shadow:0 -12px 50px rgba(15,23,42,.18);padding:10px 18px calc(18px + env(safe-area-inset-bottom))}.weekly-detail-handle{width:40px;height:4px;border-radius:999px;background:var(--line,#d8dee6);margin:1px auto 14px}.weekly-detail-head{display:flex;justify-content:space-between;gap:14px;align-items:flex-start}.weekly-detail-title{font-size:21px;font-weight:900;letter-spacing:-.45px;line-height:1.08}.weekly-detail-sub{font-size:12px;color:var(--muted,#64748b);margin-top:5px}.weekly-detail-close{appearance:none;border:0;background:var(--soft,#f1f5f9);width:34px;height:34px;border-radius:50%;font-size:22px;color:inherit;cursor:pointer;flex:0 0 auto}
      .weekly-detail-status{margin:16px 0 10px;padding:12px 13px;border-radius:14px;background:rgba(23,123,120,.08);font-size:12px;line-height:1.45}.weekly-detail-status--waiting{background:rgba(99,102,241,.08)}.weekly-detail-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:12px 0}.weekly-detail-metric{border:1px solid var(--line,#e5e7eb);border-radius:13px;padding:10px}.weekly-detail-metric span{display:block;font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:.35px;color:var(--muted,#64748b);margin-bottom:5px}.weekly-detail-metric strong{font-size:16px}.weekly-detail-meta{display:grid;gap:8px;margin:14px 0;font-size:12px}.weekly-detail-meta-row{display:flex;justify-content:space-between;gap:16px;border-bottom:1px solid var(--line,#edf0f4);padding-bottom:7px}.weekly-detail-meta-row span{color:var(--muted,#64748b)}.weekly-detail-meta-row strong{text-align:right}.weekly-detail-action{appearance:none;width:100%;border:0;border-radius:14px;padding:13px 14px;background:#177B78;color:#fff;font-weight:850;font-size:13px;cursor:pointer;margin-top:6px}
      @media (max-width:560px){.weekly-event{min-width:158px}.weekly-events-title{font-size:15px}.weekly-detail-backdrop{padding:0}.weekly-detail-sheet{border-radius:24px 24px 0 0}.weekly-detail-grid{grid-template-columns:repeat(3,minmax(82px,1fr));overflow-x:auto}}
    `;
    document.head.appendChild(style);
  }

  function ensureCard() {
    const dashboard = document.getElementById('viewDashboard');
    if (!dashboard) return null;
    let card = document.getElementById(CARD_ID);
    if (card) return card;
    card = document.createElement('div'); card.id = CARD_ID; card.className = 'card dash-secondary weekly-events-card';
    const hero = dashboard.querySelector('.card.hero');
    if (hero) hero.insertAdjacentElement('afterend', card); else dashboard.prepend(card);
    return card;
  }

  function closeDetail() { document.getElementById(DETAIL_ID)?.remove?.(); }
  function detailMetaRow(label, value) {
    const row = document.createElement('div'); row.className = 'weekly-detail-meta-row';
    const left = document.createElement('span'); left.textContent = label;
    const right = document.createElement('strong'); right.textContent = value || '—';
    row.append(left, right); return row;
  }
  function metric(label, value) {
    const box = document.createElement('div'); box.className = 'weekly-detail-metric';
    const l = document.createElement('span'); l.textContent = label;
    const v = document.createElement('strong'); v.textContent = value;
    box.append(l,v); return box;
  }

  function openDetail(event, now = new Date()) {
    if (!event) return;
    ensureStyles(); closeDetail();
    const backdrop = document.createElement('div'); backdrop.id = DETAIL_ID; backdrop.className = 'weekly-detail-backdrop'; backdrop.dataset.weeklyDetailBackdrop = '1';
    const sheet = document.createElement('section'); sheet.className = 'weekly-detail-sheet'; sheet.setAttribute('role','dialog'); sheet.setAttribute('aria-modal','true');
    const handle = document.createElement('div'); handle.className = 'weekly-detail-handle';
    const head = document.createElement('div'); head.className = 'weekly-detail-head';
    const copy = document.createElement('div'); const title = document.createElement('div'); title.className = 'weekly-detail-title'; title.textContent = event.kind === 'macro' ? event.shortTitle : event.ticker;
    const sub = document.createElement('div'); sub.className = 'weekly-detail-sub'; sub.textContent = event.kind === 'macro' ? event.title : event.name; copy.append(title, sub);
    const close = document.createElement('button'); close.type = 'button'; close.className = 'weekly-detail-close'; close.dataset.weeklyDetailClose = '1'; close.setAttribute('aria-label','Fechar'); close.textContent = '×';
    head.append(copy, close); sheet.append(handle, head);

    if (event.kind === 'macro') {
      const status = document.createElement('div'); const hasResult = hasMacroResult(event);
      status.className = `weekly-detail-status${hasResult ? '' : ' weekly-detail-status--waiting'}`;
      status.textContent = hasResult ? 'Resultado publicado. Os valores abaixo são os dados recebidos pelo snapshot Vestra.' : 'Resultado ainda não publicado no snapshot Vestra. Este painel atualiza automaticamente quando a fonte de resultados disponibilizar os números.';
      sheet.appendChild(status);
      const grid = document.createElement('div'); grid.className = 'weekly-detail-grid';
      grid.append(metric('Actual', formatResultValue(event.actual,event.unit)), metric('Consenso', formatResultValue(event.consensus,event.unit)), metric('Anterior', formatResultValue(event.previous,event.unit))); sheet.appendChild(grid);
      const meta = document.createElement('div'); meta.className = 'weekly-detail-meta';
      const fullDate = new Intl.DateTimeFormat('pt-PT',{weekday:'long',day:'numeric',month:'long'}).format(event.date);
      meta.append(detailMetaRow('Quando', `${fullDate}${event.timeLocal ? ` · ${event.timeLocal}` : ''}`), detailMetaRow('Região', event.region), detailMetaRow('Tipo', categoryLabel(event)), detailMetaRow('Fonte', sourceLabel(event.source))); sheet.appendChild(meta);
    } else {
      const status = document.createElement('div'); status.className = `weekly-detail-status${event.reported ? '' : ' weekly-detail-status--waiting'}`;
      status.textContent = event.reported ? 'Resultados publicados. Compara o EPS reportado com a estimativa e a surpresa do trimestre.' : 'Resultados ainda não publicados. A estimativa abaixo é a última disponível no snapshot Vestra.'; sheet.appendChild(status);
      const grid = document.createElement('div'); grid.className = 'weekly-detail-grid';
      grid.append(metric('EPS actual', formatEPS(event.epsActual)), metric('Estimativa', formatEPS(event.epsEstimate)), metric('Surpresa', formatSurprise(event.epsSurprisePct))); sheet.appendChild(grid);
      const meta = document.createElement('div'); meta.className = 'weekly-detail-meta';
      const fullDate = new Intl.DateTimeFormat('pt-PT',{weekday:'long',day:'numeric',month:'long'}).format(event.date);
      meta.append(detailMetaRow('Empresa', event.name), detailMetaRow('Ticker', event.ticker), detailMetaRow('Data', fullDate), detailMetaRow('Estado', event.inPortfolio ? 'No portefólio' : 'Mercado')); sheet.appendChild(meta);
      const action = document.createElement('button'); action.type = 'button'; action.className = 'weekly-detail-action'; action.dataset.weeklyDetailTicker = event.ticker; action.textContent = 'Abrir dossier da empresa'; sheet.appendChild(action);
    }
    backdrop.appendChild(sheet); document.body.appendChild(backdrop);
  }

  function render(options = {}) {
    ensureStyles(); const card = ensureCard(); if (!card) return [];
    const stocks = options.stocks || window.VestraMarketStaticUniverse?.getStocks?.() || [];
    const tickers = options.portfolioTickers || portfolioTickerSet(); const now = options.now || new Date(); const macro = options.macroEvents || macroSnapshot;
    const events = selectEvents(stocks, tickers, now, options.limit || MAX_EVENTS, macro); lastRenderedEvents = events.slice();
    const start = localDay(now); const end = new Date(start); end.setDate(end.getDate() + WINDOW_DAYS - 1); const fmt = new Intl.DateTimeFormat('pt-PT',{day:'numeric',month:'short'}); const range = `${fmt.format(start).replace('.','')} – ${fmt.format(end).replace('.','')}`;
    card.replaceChildren(); const head = document.createElement('div'); head.className = 'weekly-events-head'; const heading = document.createElement('div'); heading.innerHTML = '<div class="weekly-events-kicker">Calendário de mercado</div><div class="weekly-events-title">Eventos da semana</div>'; const rangeEl = document.createElement('div'); rangeEl.className='weekly-events-range'; rangeEl.textContent=range; head.append(heading,rangeEl); card.appendChild(head);
    if (!events.length) { const empty=document.createElement('div'); empty.className='weekly-events-empty'; empty.textContent='Sem eventos macro ou resultados relevantes nos próximos 7 dias.'; card.appendChild(empty); }
    else {
      const list=document.createElement('div'); list.className='weekly-events-list';
      events.forEach((event,index)=>{ const item=document.createElement('button'); item.type='button'; item.dataset.weeklyEventIndex=String(index); item.className=`weekly-event${event.inPortfolio?' weekly-event--portfolio':''}${event.kind==='macro'?' weekly-event--macro':''}${event.importance==='critical'?' weekly-event--critical':''}`; const day=document.createElement('div'); day.className='weekly-event__day'; day.textContent=dayLabel(event.date,now); const title=document.createElement('div'); title.className='weekly-event__ticker'; title.textContent=event.kind==='macro'?event.shortTitle:event.ticker; const name=document.createElement('div'); name.className='weekly-event__name'; name.textContent=event.kind==='macro'?`${event.region}${event.timeLocal?` · ${event.timeLocal}`:''}`:event.name; const meta=document.createElement('div'); meta.className='weekly-event__meta'; const type=document.createElement('span'); type.className='weekly-event__type'; type.textContent=categoryLabel(event); meta.appendChild(type); if(event.importance==='critical'){const high=document.createElement('span');high.className='weekly-event__critical';high.textContent='Impacto elevado';meta.appendChild(high);} if(event.inPortfolio){const owned=document.createElement('span');owned.className='weekly-event__portfolio';owned.textContent='No portefólio';meta.appendChild(owned);} item.title=event.title||event.name||event.ticker||''; item.append(day,title,name,meta); list.appendChild(item); }); card.appendChild(list);
    }
    const foot=document.createElement('div'); foot.className='weekly-events-foot'; foot.textContent='Toca num evento para ver detalhes e resultados · Macro: Fed, BLS, BEA, BCE e U.S. Census · Datas podem sofrer alterações.'; card.appendChild(foot); return events;
  }

  function openTicker(ticker) {
    const key=tickerKey(ticker); if(!key)return; closeDetail(); try{if(typeof setView==='function')setView('market');}catch(_){} setTimeout(()=>{try{const result=window.VestraMarketData?.openDossier?.(key,{origin:'dashboard-weekly-events'});if(result?.catch)result.catch(()=>{});}catch(_){}},0);
  }
  async function scheduleRender(){const marketLoad=(()=>{try{return window.VestraMarket?.ensureLoaded?.();}catch(_){return null;}})();await Promise.allSettled([marketLoad,loadMacroEvents()]);render();}
  document.addEventListener('click',event=>{const eventButton=event.target.closest?.('[data-weekly-event-index]');if(eventButton){const index=Number(eventButton.dataset.weeklyEventIndex);if(Number.isInteger(index)&&lastRenderedEvents[index])openDetail(lastRenderedEvents[index]);return;}const dossierButton=event.target.closest?.('[data-weekly-detail-ticker]');if(dossierButton){openTicker(dossierButton.dataset.weeklyDetailTicker);return;}if(event.target.closest?.('[data-weekly-detail-close]')){closeDetail();return;}const backdrop=event.target.closest?.('[data-weekly-detail-backdrop]');if(backdrop&&event.target===backdrop){closeDetail();return;}const dashboardNav=event.target.closest?.('.sidenavbtn[data-view="dashboard"]');if(dashboardNav)setTimeout(()=>render(),0);});
  window.addEventListener?.('vestra:market-ready',()=>render()); if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',scheduleRender,{once:true});else scheduleRender();
  window.VestraWeeklyEvents=Object.freeze({collectEvents,collectMacroEvents,selectEvents,loadMacroEvents,parseCalendarDate,tickerMatchesPortfolio,hasMacroResult,formatResultValue,formatEPS,formatSurprise,openDetail,render,version:VERSION});
})();
