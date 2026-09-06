/* Vestra Dashboard Weekly Events v1.0 — upcoming earnings from the compact market snapshot. */
(() => {
  'use strict';

  const VERSION = '1.0';
  const CARD_ID = 'dashboardWeeklyEventsCard';
  const STYLE_ID = 'dashboardWeeklyEventsStyle';
  const MAX_EVENTS = 8;
  const WINDOW_DAYS = 7;

  const text = value => String(value ?? '').trim();
  const number = value => {
    if (value === null || value === undefined || value === '') return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  };

  function tickerKey(value) {
    return text(value).toUpperCase();
  }

  function localDay(date) {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
  }

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
        try {
          return (typeof state !== 'undefined' && state && Array.isArray(state.assets)) ? state.assets : [];
        } catch (_) {
          return [];
        }
      },
      text,
      number,
    }) || null;
  }

  function portfolioTickerSet(context = portfolioContext()) {
    try {
      return context?.portfolioTickers?.() || new Set();
    } catch (_) {
      return new Set();
    }
  }

  function tickerMatchesPortfolio(ticker, tickers) {
    const normalized = tickerKey(ticker);
    if (!normalized) return false;
    const base = normalized.replace(/\.[A-Z]+$/, '');
    return [...(tickers || [])].some(value => {
      const candidate = tickerKey(value);
      return candidate === normalized || candidate.replace(/\.[A-Z]+$/, '') === base;
    });
  }

  function collectEvents(stocks, portfolioTickers = new Set(), now = new Date(), windowDays = WINDOW_DAYS) {
    const start = localDay(now);
    const end = new Date(start);
    end.setDate(end.getDate() + Math.max(1, Number(windowDays) || WINDOW_DAYS) - 1);

    return (Array.isArray(stocks) ? stocks : []).map(stock => {
      const date = parseCalendarDate(stock?.analyst_next_earnings_date);
      const ticker = tickerKey(stock?.ticker);
      if (!ticker || !date || date < start || date > end) return null;
      const quoteType = tickerKey(stock?.quote_type);
      if (quoteType === 'ETF' || quoteType === 'FUND' || quoteType === 'MUTUALFUND' || quoteType === 'CRYPTO') return null;
      return {
        ticker,
        name: text(stock?.name) || ticker,
        date,
        dateISO: `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`,
        marketCap: number(stock?.market_cap) || 0,
        inPortfolio: tickerMatchesPortfolio(ticker, portfolioTickers),
        source: 'analyst_next_earnings_date',
      };
    }).filter(Boolean);
  }

  function selectEvents(stocks, portfolioTickers = new Set(), now = new Date(), limit = MAX_EVENTS) {
    const events = collectEvents(stocks, portfolioTickers, now);
    const ranked = events.slice().sort((a, b) => {
      if (a.inPortfolio !== b.inPortfolio) return a.inPortfolio ? -1 : 1;
      if (a.date.getTime() !== b.date.getTime()) return a.date - b.date;
      if (a.marketCap !== b.marketCap) return b.marketCap - a.marketCap;
      return a.ticker.localeCompare(b.ticker);
    }).slice(0, Math.max(1, Number(limit) || MAX_EVENTS));

    return ranked.sort((a, b) => {
      if (a.date.getTime() !== b.date.getTime()) return a.date - b.date;
      if (a.inPortfolio !== b.inPortfolio) return a.inPortfolio ? -1 : 1;
      if (a.marketCap !== b.marketCap) return b.marketCap - a.marketCap;
      return a.ticker.localeCompare(b.ticker);
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

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
      .weekly-events-card{overflow:hidden}
      .weekly-events-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:12px}
      .weekly-events-kicker{font-size:10px;font-weight:800;letter-spacing:.55px;text-transform:uppercase;color:var(--muted,#64748b);margin-bottom:3px}
      .weekly-events-title{font-size:16px;font-weight:850;letter-spacing:-.2px;color:var(--text,#17212b)}
      .weekly-events-range{font-size:11px;color:var(--muted,#64748b);white-space:nowrap;padding-top:2px}
      .weekly-events-list{display:flex;gap:9px;overflow-x:auto;scroll-snap-type:x proximity;padding:1px 2px 5px;margin:0 -2px;-webkit-overflow-scrolling:touch;scrollbar-width:none}
      .weekly-events-list::-webkit-scrollbar{display:none}
      .weekly-event{appearance:none;border:1px solid var(--line,#e5e7eb);background:var(--card,#fff);border-radius:14px;padding:11px 12px;min-width:168px;max-width:210px;text-align:left;cursor:pointer;scroll-snap-align:start;color:inherit;box-shadow:0 1px 2px rgba(15,23,42,.025)}
      .weekly-event:active{transform:scale(.985)}
      .weekly-event--portfolio{border-color:rgba(23,123,120,.35);background:linear-gradient(180deg,rgba(23,123,120,.07),rgba(23,123,120,.025))}
      .weekly-event__day{font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.35px;color:#177B78;margin-bottom:7px}
      .weekly-event__ticker{display:flex;align-items:center;gap:7px;font-size:14px;font-weight:900;line-height:1.1;margin-bottom:4px}
      .weekly-event__name{font-size:11px;color:var(--muted,#64748b);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:9px}
      .weekly-event__meta{display:flex;align-items:center;gap:5px;flex-wrap:wrap;font-size:9px;font-weight:800}
      .weekly-event__type{padding:3px 6px;border-radius:999px;background:rgba(99,102,241,.10);color:#5558b9}
      .weekly-event__portfolio{padding:3px 6px;border-radius:999px;background:rgba(23,123,120,.12);color:#116b68}
      .weekly-events-empty{padding:12px 0 4px;color:var(--muted,#64748b);font-size:12px}
      .weekly-events-foot{margin-top:8px;font-size:9px;line-height:1.35;color:var(--muted,#64748b);opacity:.8}
      @media (max-width:560px){.weekly-event{min-width:158px}.weekly-events-title{font-size:15px}}
    `;
    document.head.appendChild(style);
  }

  function ensureCard() {
    const dashboard = document.getElementById('viewDashboard');
    if (!dashboard) return null;
    let card = document.getElementById(CARD_ID);
    if (card) return card;
    card = document.createElement('div');
    card.id = CARD_ID;
    card.className = 'card dash-secondary weekly-events-card';
    const hero = dashboard.querySelector('.card.hero');
    if (hero) hero.insertAdjacentElement('afterend', card);
    else dashboard.prepend(card);
    return card;
  }

  function render(options = {}) {
    ensureStyles();
    const card = ensureCard();
    if (!card) return [];
    const stocks = options.stocks || window.VestraMarketStaticUniverse?.getStocks?.() || [];
    const tickers = options.portfolioTickers || portfolioTickerSet();
    const now = options.now || new Date();
    const events = selectEvents(stocks, tickers, now, options.limit || MAX_EVENTS);

    const start = localDay(now);
    const end = new Date(start); end.setDate(end.getDate() + WINDOW_DAYS - 1);
    const fmt = new Intl.DateTimeFormat('pt-PT', { day: 'numeric', month: 'short' });
    const range = `${fmt.format(start).replace('.', '')} – ${fmt.format(end).replace('.', '')}`;

    card.replaceChildren();
    const head = document.createElement('div');
    head.className = 'weekly-events-head';
    const heading = document.createElement('div');
    heading.innerHTML = '<div class="weekly-events-kicker">Calendário de mercado</div><div class="weekly-events-title">Eventos da semana</div>';
    const rangeEl = document.createElement('div');
    rangeEl.className = 'weekly-events-range';
    rangeEl.textContent = range;
    head.append(heading, rangeEl);
    card.appendChild(head);

    if (!events.length) {
      const empty = document.createElement('div');
      empty.className = 'weekly-events-empty';
      empty.textContent = 'Sem resultados relevantes agendados nos próximos 7 dias.';
      card.appendChild(empty);
    } else {
      const list = document.createElement('div');
      list.className = 'weekly-events-list';
      for (const event of events) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `weekly-event${event.inPortfolio ? ' weekly-event--portfolio' : ''}`;
        button.dataset.weeklyEventTicker = event.ticker;

        const day = document.createElement('div');
        day.className = 'weekly-event__day';
        day.textContent = dayLabel(event.date, now);
        const ticker = document.createElement('div');
        ticker.className = 'weekly-event__ticker';
        ticker.textContent = event.ticker;
        const name = document.createElement('div');
        name.className = 'weekly-event__name';
        name.textContent = event.name;
        const meta = document.createElement('div');
        meta.className = 'weekly-event__meta';
        const type = document.createElement('span');
        type.className = 'weekly-event__type';
        type.textContent = 'Resultados';
        meta.appendChild(type);
        if (event.inPortfolio) {
          const owned = document.createElement('span');
          owned.className = 'weekly-event__portfolio';
          owned.textContent = 'No portefólio';
          meta.appendChild(owned);
        }
        button.append(day, ticker, name, meta);
        list.appendChild(button);
      }
      card.appendChild(list);
    }

    const foot = document.createElement('div');
    foot.className = 'weekly-events-foot';
    foot.textContent = 'Datas do feed de analistas do último snapshot Vestra · podem sofrer alterações.';
    card.appendChild(foot);
    return events;
  }

  function openTicker(ticker) {
    const key = tickerKey(ticker);
    if (!key) return;
    try { if (typeof setView === 'function') setView('market'); } catch (_) {}
    setTimeout(() => {
      try {
        const result = window.VestraMarketData?.openDossier?.(key, { origin: 'dashboard-weekly-events' });
        if (result && typeof result.catch === 'function') result.catch(() => {});
      } catch (_) {}
    }, 0);
  }

  function scheduleRender() {
    const existing = window.VestraMarketStaticUniverse?.getStocks?.() || [];
    if (existing.length) {
      render({ stocks: existing });
      return;
    }
    try {
      const load = window.VestraMarket?.ensureLoaded?.();
      if (load && typeof load.then === 'function') {
        load.then(() => render()).catch(() => render());
        return;
      }
    } catch (_) {}
    let tries = 0;
    const attempt = () => {
      const stocks = window.VestraMarketStaticUniverse?.getStocks?.() || [];
      if (stocks.length || tries >= 40) {
        render({ stocks });
        return;
      }
      tries += 1;
      setTimeout(attempt, 150);
    };
    attempt();
  }

  document.addEventListener('click', event => {
    const button = event.target.closest?.('[data-weekly-event-ticker]');
    if (button) openTicker(button.dataset.weeklyEventTicker);
    const dashboardNav = event.target.closest?.('.sidenavbtn[data-view="dashboard"]');
    if (dashboardNav) setTimeout(() => render(), 0);
  });
  window.addEventListener?.('vestra:market-ready', () => render());
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', scheduleRender, { once: true });
  else scheduleRender();

  window.VestraWeeklyEvents = Object.freeze({
    collectEvents,
    selectEvents,
    parseCalendarDate,
    tickerMatchesPortfolio,
    render,
    version: VERSION,
  });
})();
