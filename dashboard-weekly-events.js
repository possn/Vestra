/* Vestra Dashboard Weekly Events v2.2 — tappable earnings + macro catalysts with verified result details. */
(() => {
  'use strict';

  const VERSION = '2.2';
  const CARD_ID = 'dashboardWeeklyEventsCard';
  const STYLE_ID = 'dashboardWeeklyEventsStyle';
  const DETAIL_ID = 'dashboardWeeklyEventDetail';
  const MAX_EVENTS = 12;
  const WINDOW_DAYS = 7;
  const MACRO_URL = 'data/macro-events.json';
  const MACRO_FETCH_TIMEOUT_MS = 5000;
  const OFFICIAL_SOURCE_URLS = Object.freeze({
    fed: 'https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm',
    bls: 'https://www.bls.gov/bls/newsrels.htm',
    bea: 'https://www.bea.gov/news',
    ecb: 'https://www.ecb.europa.eu/press/govcdec/mopo/html/index.en.html',
    census: 'https://www.census.gov/economic-indicators/',
  });
  const OFFICIAL_SOURCE_HOSTS = Object.freeze({
    fed: ['federalreserve.gov'],
    bls: ['bls.gov'],
    bea: ['bea.gov'],
    ecb: ['ecb.europa.eu'],
    census: ['census.gov'],
  });
  const OFFICIAL_METRIC_LABELS = Object.freeze({
    headline_mom_pct: 'Headline MoM',
    headline_yoy_pct: 'Headline YoY',
    core_mom_pct: 'Core MoM',
    core_yoy_pct: 'Core YoY',
    target_lower_pct: 'Fed funds · mínimo',
    target_upper_pct: 'Fed funds · máximo',
  });
  const OFFICIAL_METRIC_SCHEMAS = new Set(['bls_cpi_v1', 'bls_ppi_v1', 'fed_funds_target_v1']);
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

  function officialSourceUrl(source, candidate = '') {
    const key = text(source).toLowerCase();
    const fallback = OFFICIAL_SOURCE_URLS[key] || '';
    const raw = text(candidate);
    if (!raw) return fallback;
    try {
      const parsed = new URL(raw);
      if (parsed.protocol !== 'https:') return fallback;
      const hostname = parsed.hostname.toLowerCase();
      const allowed = OFFICIAL_SOURCE_HOSTS[key] || [];
      const validHost = allowed.some(host => hostname === host || hostname.endsWith(`.${host}`));
      return validHost ? parsed.href : fallback;
    } catch (_) {
      return fallback;
    }
  }

  function normaliseOfficialMetrics(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return Object.freeze({});
    const out = {};
    for (const key of Object.keys(OFFICIAL_METRIC_LABELS)) {
      const parsed = number(value[key]);
      if (parsed !== null) out[key] = parsed;
    }
    return Object.freeze(out);
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
      const source = text(row?.source);
      const resultMetricSchema = text(row?.result_metric_schema);
      return {
        kind: 'macro',
        id: `${source || 'macro'}:${text(row?.date)}:${text(row?.short_title) || index}`,
        title: text(row?.title) || text(row?.short_title) || 'Evento macro',
        shortTitle: text(row?.short_title) || text(row?.title) || 'Macro',
        date: eventStart < start ? start : eventStart,
        dateEnd: eventEnd,
        region: text(row?.region), category: text(row?.category),
        importance: text(row?.importance) || 'high', timeLocal: text(row?.time_local),
        source,
        sourceUrl: officialSourceUrl(source, row?.source_url),
        actual: row?.actual ?? null,
        consensus: row?.consensus ?? row?.forecast ?? null,
        previous: row?.previous ?? null,
        unit: text(row?.unit), resultStatus: text(row?.result_status),
        resultSummary: text(row?.result_summary),
        resultReleasedAt: text(row?.result_released_at),
        resultMetricSchema: OFFICIAL_METRIC_SCHEMAS.has(resultMetricSchema) ? resultMetricSchema : '',
        resultMetrics: normaliseOfficialMetrics(row?.result_metrics),
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

  function hasOfficialMacroSummary(event) {
    return text(event?.resultStatus) === 'official_release_summary' && text(event?.resultSummary) !== '';
  }

  function hasStructuredOfficialMetrics(event) {
    return OFFICIAL_METRIC_SCHEMAS.has(text(event?.resultMetricSchema)) && Object.keys(event?.resultMetrics || {}).length > 0;
  }

  function hasMacroPublication(event) {
    return hasMacroResult(event) || hasOfficialMacroSummary(event) || hasStructuredOfficialMetrics(event);
  }

  function hasMacroMetrics(event) {
    return [event?.actual, event?.consensus, event?.previous].some(value => value !== null && value !== undefined && text(value) !== '');
  }

  function formatResultValue(value, unit = '') {
    if (value === null || value === undefined || text(value) === '') return '—';
    return `${text(value)}${unit ? ` ${unit}` : ''}`;
  }

  function formatOfficialPercent(value) {
    const parsed = number(value);
    if (parsed === null) return '—';
    const sign = parsed > 0 ? '+' : '';
    return `${sign}${parsed.toLocaleString('pt-PT', { minimumFractionDigits: 1, maximumFractionDigits: 2 })}%`;
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

  async function loadMacroEvents(fetchImpl = (...args) => fetch(...args), timeoutMs = MACRO_FETCH_TIMEOUT_MS, force = false) {
    if (macroSnapshot && !force) return macroSnapshot;
    if (macroLoading) return macroLoading;
    let timeoutId = null;
    macroLoading = (async () => {
      try {
        const request = (async () => {
          try {
            const response = await fetchImpl(MACRO_URL, { cache: 'no-store' });
            if (!response.ok) return null;
            const payload = await response.json();
            return payload && Array.isArray(payload.events) ? payload : null;
          } catch (_) { return null; }
        })();
        const timeout = new Promise(resolve => {
          timeoutId = setTimeout(() => resolve(null), Math.max(1, Number(timeoutMs) || MACRO_FETCH_TIMEOUT_MS));
        });
        const payload = await Promise.race([request, timeout]);
        if (!payload) return macroSnapshot;
        macroSnapshot = payload;
        return macroSnapshot;
      } finally {
        if (timeoutId !== null) clearTimeout(timeoutId);
        macroLoading = null;
      }
    })();
    return macroLoading;
  }

  async function refreshMacroEvents() {
    const latest = await loadMacroEvents((...args) => fetch(...args), MACRO_FETCH_TIMEOUT_MS, true);
    if (latest) {
      const nav = window.VestraWeeklyEventsNavigation;
      const now = nav?.shiftedDate ? nav.shiftedDate(new Date()) : new Date();
      render({ now });
      window.dispatchEvent?.(new CustomEvent('vestra:weekly-data-refreshed'));
    }
    return latest;
  }

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const link = document.createElement('link');
    link.id = STYLE_ID;
    link.rel = 'stylesheet';
    link.href = 'dashboard-weekly-events.css?v=1.0';
    document.head.appendChild(link);
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
  function officialSummary(summary) {
    const box = document.createElement('div'); box.className = 'weekly-detail-summary';
    const label = document.createElement('div'); label.className = 'weekly-detail-summary__label'; label.textContent = 'Resumo oficial';
    const body = document.createElement('div'); body.className = 'weekly-detail-summary__text'; body.textContent = text(summary);
    box.append(label, body); return box;
  }
  function officialMetricGrid(event) {
    if (!hasStructuredOfficialMetrics(event)) return null;
    const grid = document.createElement('div'); grid.className = 'weekly-detail-grid weekly-detail-grid--official';
    for (const [key, label] of Object.entries(OFFICIAL_METRIC_LABELS)) {
      if (!Object.prototype.hasOwnProperty.call(event.resultMetrics, key)) continue;
      grid.appendChild(metric(label, formatOfficialPercent(event.resultMetrics[key])));
    }
    return grid.childElementCount ? grid : null;
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
      const hasActual = hasMacroResult(event);
      const hasSummary = hasOfficialMacroSummary(event);
      const hasOfficialMetrics = hasStructuredOfficialMetrics(event);
      const published = hasMacroPublication(event);
      const status = document.createElement('div');
      status.className = `weekly-detail-status${published ? '' : ' weekly-detail-status--waiting'}`;
      status.textContent = hasActual
        ? 'Resultado publicado. Os valores abaixo são os dados estruturados recebidos pelo snapshot Vestra.'
        : hasOfficialMetrics
          ? 'Publicação oficial disponível. A Vestra apresenta abaixo as métricas explicitamente identificadas na fonte oficial.'
          : hasSummary
            ? 'Publicação oficial disponível. A Vestra validou a data da release e apresenta abaixo o resumo oficial, sem inferir uma métrica “Actual” ambígua.'
            : 'Resultado ainda não publicado no snapshot Vestra. Este painel volta a consultar o snapshot ao abrir o evento e quando a app regressa ao primeiro plano.';
      sheet.appendChild(status);
      const officialGrid = officialMetricGrid(event);
      if (officialGrid) sheet.appendChild(officialGrid);
      if (hasSummary) sheet.appendChild(officialSummary(event.resultSummary));
      if (hasMacroMetrics(event)) {
        const grid = document.createElement('div'); grid.className = 'weekly-detail-grid';
        grid.append(metric('Actual', formatResultValue(event.actual,event.unit)), metric('Consenso', formatResultValue(event.consensus,event.unit)), metric('Anterior', formatResultValue(event.previous,event.unit))); sheet.appendChild(grid);
      }
      const meta = document.createElement('div'); meta.className = 'weekly-detail-meta';
      const fullDate = new Intl.DateTimeFormat('pt-PT',{weekday:'long',day:'numeric',month:'long'}).format(event.date);
      meta.append(detailMetaRow('Quando', `${fullDate}${event.timeLocal ? ` · ${event.timeLocal}` : ''}`), detailMetaRow('Região', event.region), detailMetaRow('Tipo', categoryLabel(event)), detailMetaRow('Fonte', sourceLabel(event.source)));
      if (published && event.resultReleasedAt) meta.append(detailMetaRow('Publicação validada', event.resultReleasedAt));
      sheet.appendChild(meta);
      if (event.sourceUrl) {
        const action = document.createElement('a');
        action.className = 'weekly-detail-action';
        action.href = event.sourceUrl;
        action.dataset.weeklyReturnEventId = event.id || '';
        action.target = '_blank';
        action.rel = 'noopener noreferrer';
        action.textContent = 'Ver publicação oficial';
        sheet.appendChild(action);
      }
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
    const key=tickerKey(ticker); if(!key)return false;
    closeDetail();
    const nav=window.VestraNavigation;
    if(!nav?.openCompany)return false;
    void nav.openCompany(key,{origin:'market'});
    return true;
  }
  function findMacroEventById(snapshot, detailId) {
    const id = text(detailId);
    if (!id || !snapshot) return null;
    const current = lastRenderedEvents.find(item => item.kind === 'macro' && item.id === id);
    if (current) return current;

    // A cold iOS/PWA resume can happen after midnight. In that case the event
    // the user opened may already sit just outside the new forward-looking
    // weekly window. Rebuild only the saved event's own calendar day so the
    // exact official detail can still be restored without changing the card's
    // current-week contents.
    const match = /^[^:]+:(\\d{4}-\\d{2}-\\d{2}):/.exec(id);
    const eventDay = match ? parseCalendarDate(match[1]) : null;
    if (!eventDay) return null;
    return collectMacroEvents(snapshot, eventDay, 1).find(item => item.id === id) || null;
  }

  function restoreExternalWeeklyDetail() {
    const context = window.__vestraExternalReturnContext;
    if (!context || context.kind !== 'weekly-official' || !context.detailId) return false;
    const selected = findMacroEventById(macroSnapshot, context.detailId);
    if (!selected) return false;
    openDetail(selected);
    context.detailId = '';
    return true;
  }

  async function scheduleRender(){
    const marketLoad=(()=>{try{return window.VestraMarket?.ensureLoaded?.();}catch(_){return null;}})();
    await Promise.allSettled([marketLoad,loadMacroEvents()]);
    render();
    restoreExternalWeeklyDetail();
  }
  document.addEventListener('click',event=>{
    const officialLink=event.target.closest?.('a.weekly-detail-action[href]');
    if(officialLink){
      outboundOfficialPending=true;
      window.VestraUiCore?.rememberExternalReturnContext?.({
        kind:'weekly-official',
        view:'dashboard',
        detailId:String(officialLink.dataset.weeklyReturnEventId||''),
        scrollY:Math.max(0,Number(window.scrollY||document.scrollingElement?.scrollTop||0)),
      });
    }
    const eventButton=event.target.closest?.('[data-weekly-event-index]');
    if(eventButton){
      const index=Number(eventButton.dataset.weeklyEventIndex);
      const selected=Number.isInteger(index)?lastRenderedEvents[index]:null;
      if(selected){
        openDetail(selected);
        if(selected.kind==='macro'){
          const id=selected.id;
          void refreshMacroEvents().then(()=>{
            const fresh=lastRenderedEvents.find(item=>item.kind==='macro'&&item.id===id);
            if(fresh&&document.getElementById(DETAIL_ID))openDetail(fresh);
          });
        }
      }
      return;
    }
    const dossierButton=event.target.closest?.('[data-weekly-detail-ticker]');if(dossierButton){openTicker(dossierButton.dataset.weeklyDetailTicker);return;}
    if(event.target.closest?.('[data-weekly-detail-close]')){closeDetail();return;}
    const backdrop=event.target.closest?.('[data-weekly-detail-backdrop]');if(backdrop&&event.target===backdrop){closeDetail();return;}
    const dashboardNav=event.target.closest?.('.sidenavbtn[data-view="dashboard"]');if(dashboardNav)void refreshMacroEvents();
  });
  let wasBackgrounded=false;
  let outboundOfficialPending=false;
  let weeklyRefreshPending=false;
  const resumeWeeklyEvents=()=>{
    if(!wasBackgrounded&&!outboundOfficialPending)return false;
    if(weeklyRefreshPending)return true;
    wasBackgrounded=false;
    outboundOfficialPending=false;
    weeklyRefreshPending=true;
    void refreshMacroEvents().finally(()=>{weeklyRefreshPending=false;});
    return true;
  };
  document.addEventListener('visibilitychange',()=>{
    if(document.visibilityState==='hidden'){wasBackgrounded=true;return;}
    if(document.visibilityState==='visible')resumeWeeklyEvents();
  });
  window.addEventListener?.('focus',resumeWeeklyEvents);
  window.addEventListener?.('pageshow',resumeWeeklyEvents);
  window.addEventListener?.('vestra:market-ready',()=>render()); if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',scheduleRender,{once:true});else scheduleRender();
  window.VestraWeeklyEvents=Object.freeze({collectEvents,collectMacroEvents,selectEvents,loadMacroEvents,refreshMacroEvents,parseCalendarDate,tickerMatchesPortfolio,officialSourceUrl,normaliseOfficialMetrics,hasMacroResult,hasOfficialMacroSummary,hasStructuredOfficialMetrics,hasMacroPublication,hasMacroMetrics,formatResultValue,formatOfficialPercent,formatEPS,formatSurprise,openDetail,render,openTicker,findMacroEventById,restoreExternalWeeklyDetail,macroFetchTimeoutMs:MACRO_FETCH_TIMEOUT_MS,version:VERSION});
})();