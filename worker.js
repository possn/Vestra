/**
 * Cloudflare Worker — Proxy de Cotações (Yahoo Finance)
 * Versão 4.0 — quotes + live market detail + chart enrichment
 */

const CACHE_TTL = 300; // 5 minutos

const TICKER_ALIASES = {
  "MPW.US": "MPW",
  "MPW": "MPW",
  "UNA": "UNA.AS",
  "UNA.L": "UNA.AS",
  "UNA.DE": "UNA.AS",
  "UNA.PA": "UNA.AS",
  "UNA.AS": "UNA.AS",
  "CRSP": "CRSP",
  "CRSP.SW": "CRSP"
};

function corsHeaders(origin) {
  // Vestra is served from possn.github.io. Match the exact browser origin;
  // local loopback remains available for development. CORS is not auth, but
  // this prevents unrelated GitHub/Cloudflare Pages sites from reading responses.
  let allowed = !origin;
  if (origin) {
    try {
      const u = new URL(origin);
      const host = u.hostname.toLowerCase();
      const vestraPages = u.protocol === "https:" && u.origin === "https://possn.github.io";
      const local = host === "localhost" || host === "127.0.0.1" || host === "::1";
      const localDev = local && (u.protocol === "http:" || u.protocol === "https:");
      allowed = vestraPages || localDev;
    } catch (_) {
      allowed = false;
    }
  }
  return {
    "Access-Control-Allow-Origin": allowed ? (origin || "*") : "null",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  };
}

function normCcy(price, ccy) {
  if (ccy === "GBp" || ccy === "GBX") return { price: price / 100, ccy: "GBP" };
  return { price, ccy: ccy || "USD" };
}

function normalizeInputTicker(raw) {
  const t = String(raw || "").trim().toUpperCase();
  return TICKER_ALIASES[t] || t;
}

function uniqueNonEmpty(arr) {
  return [...new Set((arr || []).map(v => String(v || '').trim().toUpperCase()).filter(Boolean))];
}

async function fetchJsonMaybe(url, init) {
  const resp = await fetch(url, init);
  if (!resp.ok) return null;
  try { return await resp.json(); } catch (_) { return null; }
}

function positiveNumber(...vals) {
  for (const v of vals) if (Number.isFinite(v) && v > 0) return v;
  return null;
}

async function fetchYahooQuoteCore(ticker, ctx) {
  const cacheKey = `quote41:${ticker.toUpperCase()}`;
  const cache = caches.default;
  const cacheUrl = `https://cache.internal/${cacheKey}`;

  const cached = await cache.match(cacheUrl);
  if (cached) {
    const data = await cached.json();
    data._cached = true;
    return data;
  }

  const headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9"
  };

  const quoteUrls = [
    `https://query1.finance.yahoo.com/v7/finance/quote?symbols=${encodeURIComponent(ticker)}`,
    `https://query2.finance.yahoo.com/v7/finance/quote?symbols=${encodeURIComponent(ticker)}`
  ];
  for (const url of quoteUrls) {
    try {
      const d = await fetchJsonMaybe(url, { headers });
      const q = d?.quoteResponse?.result?.[0];
      const rawPrice = positiveNumber(
        q?.regularMarketPrice, q?.postMarketPrice, q?.preMarketPrice,
        q?.regularMarketPreviousClose, q?.regularMarketOpen, q?.bid, q?.ask
      );
      if (q && rawPrice) {
        const { price, ccy } = normCcy(rawPrice, q.currency);
        const result = {
          ticker: ticker.toUpperCase(),
          price,
          currency: ccy,
          name: q.shortName || q.longName || ticker,
          change_pct: Number.isFinite(q.regularMarketChangePercent) ? q.regularMarketChangePercent : 0,
          sector: q.sector || "",
          industry: q.industry || "",
          country: q.country || "",
          exchange: q.exchange || q.fullExchangeName || "",
          quote_type: q.quoteType || "",
          market_cap: Number.isFinite(q.marketCap) ? q.marketCap : null,
          trailing_pe: Number.isFinite(q.trailingPE) ? q.trailingPE : null,
          forward_pe: Number.isFinite(q.forwardPE) ? q.forwardPE : null,
          price_to_book: Number.isFinite(q.priceToBook) ? q.priceToBook : null,
          eps_ttm: Number.isFinite(q.epsTrailingTwelveMonths) ? q.epsTrailingTwelveMonths : null,
          eps_forward: Number.isFinite(q.epsForward) ? q.epsForward : null,
          fifty_two_week_high: Number.isFinite(q.fiftyTwoWeekHigh) ? q.fiftyTwoWeekHigh : null,
          fifty_two_week_low: Number.isFinite(q.fiftyTwoWeekLow) ? q.fiftyTwoWeekLow : null,
          // Dividend data from Yahoo Finance
          div_rate: Number.isFinite(q.trailingAnnualDividendRate) ? q.trailingAnnualDividendRate : 0,
          div_yield: Number.isFinite(q.trailingAnnualDividendYield) ? q.trailingAnnualDividendYield : 0,
          ex_div_date: q.exDividendDate ? new Date(q.exDividendDate * 1000).toISOString().slice(0,10) : "",
          div_date: q.dividendDate ? new Date(q.dividendDate * 1000).toISOString().slice(0,10) : "",
          updated: new Date().toISOString(),
        };
        ctx.waitUntil(cache.put(cacheUrl, new Response(JSON.stringify(result), {
          headers: { "Content-Type": "application/json", "Cache-Control": `public, max-age=${CACHE_TTL}` }
        })));
        return result;
      }
    } catch (_) {}
  }

  const chartUrls = [
    `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker)}?interval=1d&range=5d`,
    `https://query2.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker)}?interval=1d&range=5d`
  ];
  for (const url of chartUrls) {
    try {
      const json = await fetchJsonMaybe(url, { headers, cf: { cacheTtl: CACHE_TTL, cacheEverything: false } });
      const result0 = json?.chart?.result?.[0];
      const meta = result0?.meta;
      const closes = result0?.indicators?.quote?.[0]?.close || [];
      const lastClose = [...closes].reverse().find(v => Number.isFinite(v) && v > 0);
      const rawPrice = positiveNumber(meta?.regularMarketPrice, meta?.previousClose, lastClose);
      if (meta && rawPrice) {
        const { price, ccy } = normCcy(rawPrice, meta.currency);
        const result = {
          ticker: ticker.toUpperCase(),
          price,
          currency: ccy,
          name: meta.shortName || meta.symbol || ticker,
          change_pct: (Number.isFinite(meta.regularMarketPrice) && Number.isFinite(meta.previousClose) && meta.previousClose > 0)
            ? ((meta.regularMarketPrice - meta.previousClose) / meta.previousClose) * 100 : 0,
          sector: "",
          industry: "",
          country: "",
          exchange: meta.exchangeName || "",
          quote_type: meta.instrumentType || "",
          updated: new Date().toISOString(),
        };
        ctx.waitUntil(cache.put(cacheUrl, new Response(JSON.stringify(result), {
          headers: { "Content-Type": "application/json", "Cache-Control": `public, max-age=${CACHE_TTL}` }
        })));
        return result;
      }
    } catch (_) {}
  }

  const qsUrls = [
    `https://query1.finance.yahoo.com/v10/finance/quoteSummary/${encodeURIComponent(ticker)}?modules=price`,
    `https://query2.finance.yahoo.com/v10/finance/quoteSummary/${encodeURIComponent(ticker)}?modules=price`
  ];
  for (const url of qsUrls) {
    try {
      const qsJson = await fetchJsonMaybe(url, { headers });
      const priceNode = qsJson?.quoteSummary?.result?.[0]?.price;
      const rawPrice = positiveNumber(
        priceNode?.regularMarketPrice?.raw,
        priceNode?.regularMarketPreviousClose?.raw,
        priceNode?.postMarketPrice?.raw,
        priceNode?.preMarketPrice?.raw
      );
      if (rawPrice) {
        const { price, ccy } = normCcy(rawPrice, priceNode?.currency);
        const result = {
          ticker: ticker.toUpperCase(),
          price,
          currency: ccy,
          name: priceNode?.shortName || priceNode?.longName || ticker,
          change_pct: Number.isFinite(priceNode?.regularMarketChangePercent?.raw) ? priceNode.regularMarketChangePercent.raw : 0,
          sector: "", industry: "", country: "",
          exchange: priceNode?.exchangeName || priceNode?.exchange || "",
          quote_type: priceNode?.quoteType || "",
          updated: new Date().toISOString(),
        };
        ctx.waitUntil(cache.put(cacheUrl, new Response(JSON.stringify(result), {
          headers: { "Content-Type": "application/json", "Cache-Control": `public, max-age=${CACHE_TTL}` }
        })));
        return result;
      }
    } catch (_) {}
  }

  // Último recurso: página HTML do Yahoo (útil quando as APIs devolvem 404 inconsistentes)
  try {
    const resp = await fetch(`https://finance.yahoo.com/quote/${encodeURIComponent(ticker)}`, { headers });
    if (resp.ok) {
      const html = await resp.text();
      const rawPriceMatch = html.match(/"regularMarketPrice":\{"raw":([0-9]+(?:\.[0-9]+)?)/);
      const prevCloseMatch = html.match(/"regularMarketPreviousClose":\{"raw":([0-9]+(?:\.[0-9]+)?)/);
      const ccyMatch = html.match(/"currency":"([A-Z]{3,4})"/);
      const nameMatch = html.match(/"shortName":"([^"]+)"/) || html.match(/<title>([^<]+?) \(/i);
      const rawPrice = positiveNumber(rawPriceMatch ? Number(rawPriceMatch[1]) : null, prevCloseMatch ? Number(prevCloseMatch[1]) : null);
      if (rawPrice) {
        const { price, ccy } = normCcy(rawPrice, ccyMatch ? ccyMatch[1] : "USD");
        const result = {
          ticker: ticker.toUpperCase(),
          price,
          currency: ccy,
          name: nameMatch ? String(nameMatch[1]).replace(/\u002F/g, '/').trim() : ticker,
          change_pct: 0, sector: "", industry: "", country: "", exchange: "", quote_type: "",
          updated: new Date().toISOString(),
        };
        ctx.waitUntil(cache.put(cacheUrl, new Response(JSON.stringify(result), {
          headers: { "Content-Type": "application/json", "Cache-Control": `public, max-age=${CACHE_TTL}` }
        })));
        return result;
      }
    }
  } catch (_) {}

  throw new Error(`Sem dados para ${ticker}`);
}

async function fetchYahooQuote(ticker, ctx) {
  const raw = String(ticker || '').trim().toUpperCase();
  const canonical = normalizeInputTicker(raw);
  const candidates = uniqueNonEmpty([canonical, raw]);
  let lastErr = null;
  for (const tk of candidates) {
    try {
      return await fetchYahooQuoteCore(tk, ctx);
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr || new Error(`Sem dados para ${canonical || raw}`);
}


function raw(node) {
  if (node == null) return null;
  if (typeof node === 'number' || typeof node === 'string') return node;
  return node.raw ?? node.fmt ?? null;
}

function pctRaw(node) {
  const v = Number(raw(node));
  if (!Number.isFinite(v)) return null;
  return Math.abs(v) <= 1 ? v * 100 : v;
}

function isoFromUnix(v) {
  const n = Number(raw(v));
  if (!Number.isFinite(n) || n <= 0) return '';
  return new Date(n * 1000).toISOString().slice(0,10);
}



function latestTimeseriesValue(series) {
  if (!Array.isArray(series) || !series.length) return null;
  const sorted = [...series].sort((a,b) => Number(a?.asOfDate?.replaceAll?.('-','') || 0) - Number(b?.asOfDate?.replaceAll?.('-','') || 0));
  for (let i=sorted.length-1; i>=0; i--) {
    const v = Number(raw(sorted[i]?.reportedValue));
    if (Number.isFinite(v)) return v;
  }
  return null;
}

function previousTimeseriesValue(series) {
  if (!Array.isArray(series) || series.length < 2) return null;
  const vals = [...series].sort((a,b) => String(a?.asOfDate||'').localeCompare(String(b?.asOfDate||'')))
    .map(x => Number(raw(x?.reportedValue))).filter(Number.isFinite);
  return vals.length >= 2 ? vals[vals.length-2] : null;
}

function growthPct(current, previous) {
  if (!Number.isFinite(current) || !Number.isFinite(previous) || previous === 0) return null;
  return ((current / Math.abs(previous)) - (previous < 0 ? -1 : 1)) * 100;
}

async function fetchYahooFundamentalTimeseries(ticker, headers) {
  // Yahoo quoteSummary is frequently sparse for LSE/Euronext names. The
  // fundamentals-timeseries endpoint often still exposes the statements.
  const now = Math.floor(Date.now()/1000);
  const period1 = now - 60*60*24*365*4;
  const types = [
    'annualTotalRevenue','quarterlyTotalRevenue',
    'annualNetIncome','quarterlyNetIncome',
    'annualDilutedEPS','quarterlyDilutedEPS',
    'annualFreeCashFlow','quarterlyFreeCashFlow',
    'annualOperatingCashFlow','quarterlyOperatingCashFlow',
    'annualEBITDA','quarterlyEBITDA',
    'annualTotalDebt','quarterlyTotalDebt',
    'annualCashCashEquivalentsAndShortTermInvestments','quarterlyCashCashEquivalentsAndShortTermInvestments',
    'annualStockholdersEquity','quarterlyStockholdersEquity',
    'annualGrossProfit','quarterlyGrossProfit',
    'annualOperatingIncome','quarterlyOperatingIncome'
  ];
  let json = null;
  for (const host of ['query1.finance.yahoo.com','query2.finance.yahoo.com']) {
    try {
      const u = `https://${host}/ws/fundamentals-timeseries/v1/finance/timeseries/${encodeURIComponent(ticker)}?symbol=${encodeURIComponent(ticker)}&type=${types.join(',')}&period1=${period1}&period2=${now}`;
      const d = await fetchJsonMaybe(u, { headers });
      if (Array.isArray(d?.timeseries?.result)) { json=d; break; }
    } catch (_) {}
  }
  const out = {};
  for (const block of (json?.timeseries?.result || [])) {
    const key = (block?.meta?.type?.[0] || block?.type || '').toString();
    if (key) out[key] = block[key] || block.timeseries || [];
  }
  return out;
}

function firstFinite(...vals) {
  for (const v of vals) if (Number.isFinite(v)) return v;
  return null;
}

async function fetchYahooMarketDetail(ticker, ctx) {
  const canonical = normalizeInputTicker(ticker);
  const cache = caches.default;
  const cacheUrl = `https://cache.internal/market41:${canonical}`;
  const cached = await cache.match(cacheUrl);
  if (cached) {
    const data = await cached.json();
    data._cached = true;
    return data;
  }

  const headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9"
  };
  const modules = [
    'price','summaryDetail','defaultKeyStatistics','financialData','assetProfile',
    'calendarEvents','earningsTrend','recommendationTrend'
  ].join(',');
  let qs = null;
  for (const host of ['query1.finance.yahoo.com','query2.finance.yahoo.com']) {
    try {
      const data = await fetchJsonMaybe(`https://${host}/v10/finance/quoteSummary/${encodeURIComponent(canonical)}?modules=${modules}`, { headers });
      if (data?.quoteSummary?.result?.[0]) { qs = data.quoteSummary.result[0]; break; }
    } catch (_) {}
  }

  const quote = await fetchYahooQuote(canonical, ctx);
  const price = qs?.price || {};
  const sd = qs?.summaryDetail || {};
  const ks = qs?.defaultKeyStatistics || {};
  const fd = qs?.financialData || {};
  const ap = qs?.assetProfile || {};
  const ce = qs?.calendarEvents || {};
  const rt = qs?.recommendationTrend?.trend?.[0] || {};
  const et = Array.isArray(qs?.earningsTrend?.trend) ? qs.earningsTrend.trend : [];
  const nextYear = et.find(x => x.period === '+1y') || et.find(x => x.period === '+1q') || {};

  let ts = {};
  try { ts = await fetchYahooFundamentalTimeseries(canonical, headers); } catch (_) {}

  const revAnnual = latestTimeseriesValue(ts.annualTotalRevenue);
  const revPrev = previousTimeseriesValue(ts.annualTotalRevenue);
  const niAnnual = latestTimeseriesValue(ts.annualNetIncome);
  const niPrev = previousTimeseriesValue(ts.annualNetIncome);
  const epsAnnual = latestTimeseriesValue(ts.annualDilutedEPS);
  const epsPrev = previousTimeseriesValue(ts.annualDilutedEPS);
  const fcfAnnual = firstFinite(latestTimeseriesValue(ts.annualFreeCashFlow), latestTimeseriesValue(ts.quarterlyFreeCashFlow));
  const ocfAnnual = firstFinite(latestTimeseriesValue(ts.annualOperatingCashFlow), latestTimeseriesValue(ts.quarterlyOperatingCashFlow));
  const ebitdaAnnual = firstFinite(latestTimeseriesValue(ts.annualEBITDA), latestTimeseriesValue(ts.quarterlyEBITDA));
  const debtAnnual = firstFinite(latestTimeseriesValue(ts.annualTotalDebt), latestTimeseriesValue(ts.quarterlyTotalDebt));
  const equityAnnual = firstFinite(latestTimeseriesValue(ts.annualStockholdersEquity), latestTimeseriesValue(ts.quarterlyStockholdersEquity));
  const cashAnnual = firstFinite(latestTimeseriesValue(ts.annualCashCashEquivalentsAndShortTermInvestments), latestTimeseriesValue(ts.quarterlyCashCashEquivalentsAndShortTermInvestments));
  const grossAnnual = firstFinite(latestTimeseriesValue(ts.annualGrossProfit), latestTimeseriesValue(ts.quarterlyGrossProfit));
  const opIncomeAnnual = firstFinite(latestTimeseriesValue(ts.annualOperatingIncome), latestTimeseriesValue(ts.quarterlyOperatingIncome));

  let history = [];
  try {
    const cj = await fetchJsonMaybe(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(canonical)}?interval=1d&range=1y`, { headers });
    const r = cj?.chart?.result?.[0];
    const ts = r?.timestamp || [];
    const closes = r?.indicators?.quote?.[0]?.close || [];
    history = ts.map((t,i)=>({date:new Date(t*1000).toISOString().slice(0,10),close:Number(closes[i])})).filter(x=>Number.isFinite(x.close));
  } catch (_) {}

  const marketCap = Number(raw(price.marketCap) ?? raw(sd.marketCap));
  const fcf = Number(raw(fd.freeCashflow));
  const target = Number(raw(fd.targetMeanPrice));
  const current = Number(quote.price);
  const result = {
    ticker: canonical,
    name: raw(price.longName) || raw(price.shortName) || quote.name || canonical,
    current_price: Number.isFinite(current) ? current : null,
    currency: raw(price.currency) || quote.currency || 'USD',
    exchange: raw(price.exchangeName) || quote.exchange || '',
    quote_type: raw(price.quoteType) || quote.quote_type || '',
    sector: ap.sector || quote.sector || '',
    industry: ap.industry || quote.industry || '',
    country: ap.country || quote.country || '',
    business_summary: ap.longBusinessSummary || '',
    market_cap: firstFinite(Number.isFinite(marketCap) ? marketCap : null, Number(quote.market_cap)),
    trailing_pe: firstFinite(Number(raw(sd.trailingPE)), Number(raw(ks.trailingPE)), Number(quote.trailing_pe)),
    forward_pe: firstFinite(Number(raw(sd.forwardPE)), Number(raw(ks.forwardPE)), Number(quote.forward_pe)),
    price_to_book: firstFinite(Number(raw(ks.priceToBook)), Number(quote.price_to_book)),
    enterprise_to_ebitda: Number(raw(ks.enterpriseToEbitda)),
    dividend_yield: pctRaw(sd.dividendYield),
    roe: pctRaw(fd.returnOnEquity),
    roa: pctRaw(fd.returnOnAssets),
    revenue_growth: firstFinite(pctRaw(fd.revenueGrowth), growthPct(revAnnual, revPrev)),
    earnings_growth: firstFinite(pctRaw(fd.earningsGrowth), growthPct(niAnnual, niPrev)),
    eps_growth: growthPct(epsAnnual, epsPrev),
    profit_margin: firstFinite(pctRaw(fd.profitMargins), Number.isFinite(niAnnual) && Number.isFinite(revAnnual) && revAnnual !== 0 ? niAnnual/revAnnual*100 : null),
    operating_margin: firstFinite(pctRaw(fd.operatingMargins), Number.isFinite(opIncomeAnnual) && Number.isFinite(revAnnual) && revAnnual !== 0 ? opIncomeAnnual/revAnnual*100 : null),
    gross_margin: firstFinite(pctRaw(fd.grossMargins), Number.isFinite(grossAnnual) && Number.isFinite(revAnnual) && revAnnual !== 0 ? grossAnnual/revAnnual*100 : null),
    operating_cash_flow: firstFinite(Number(raw(fd.operatingCashflow)), ocfAnnual),
    free_cash_flow: firstFinite(Number.isFinite(fcf) ? fcf : null, fcfAnnual),
    fcf_yield: Number.isFinite(firstFinite(Number.isFinite(fcf) ? fcf : null, fcfAnnual)) && Number.isFinite(marketCap) && marketCap > 0 ? (firstFinite(Number.isFinite(fcf) ? fcf : null, fcfAnnual) / marketCap) * 100 : null,
    ebitda: ebitdaAnnual,
    total_debt: debtAnnual,
    cash_and_short_term_investments: cashAnnual,
    net_cash: Number.isFinite(cashAnnual) && Number.isFinite(debtAnnual) ? cashAnnual - debtAnnual : null,
    stockholders_equity: equityAnnual,
    debt_to_equity: firstFinite(Number(raw(fd.debtToEquity)), Number.isFinite(debtAnnual) && Number.isFinite(equityAnnual) && equityAnnual !== 0 ? debtAnnual/equityAnnual*100 : null),
    current_ratio: Number(raw(fd.currentRatio)),
    quick_ratio: Number(raw(fd.quickRatio)),
    analyst_price_target_mean: Number.isFinite(target) ? target : null,
    analyst_price_target_upside_pct: Number.isFinite(target) && Number.isFinite(current) && current > 0 ? ((target/current)-1)*100 : null,
    analyst_strong_buy: Number(rt.strongBuy || 0),
    analyst_buy: Number(rt.buy || 0),
    analyst_hold: Number(rt.hold || 0),
    analyst_sell: Number(rt.sell || 0),
    analyst_strong_sell: Number(rt.strongSell || 0),
    analyst_eps_next_y_growth: pctRaw(nextYear?.growth),
    analyst_next_earnings_date: isoFromUnix(ce?.earnings?.earningsDate?.[0]),
    fifty_two_week_high: Number(raw(sd.fiftyTwoWeekHigh)),
    fifty_two_week_low: Number(raw(sd.fiftyTwoWeekLow)),
    beta: Number(raw(ks.beta)),
    revenue_latest: revAnnual,
    net_income_latest: niAnnual,
    eps_latest: epsAnnual,
    price_history_1y: history,
    updated: new Date().toISOString(),
    source: qs ? 'Yahoo Finance quoteSummary + fundamentals-timeseries + chart' : 'Yahoo Finance fundamentals-timeseries + quote/chart'
  };
  for (const k of Object.keys(result)) if (typeof result[k] === 'number' && !Number.isFinite(result[k])) result[k] = null;
  ctx.waitUntil(cache.put(cacheUrl, new Response(JSON.stringify(result), {
    headers: { "Content-Type": "application/json", "Cache-Control": "public, max-age=300" }
  })));
  return result;
}



function normalizeCongressTrade(x) {
  const ticker = String(x?.ticker || x?.symbol || '').toUpperCase();
  const rawType = String(x?.type || x?.transaction_type || x?.transaction || '').toLowerCase();
  const type = rawType.includes('sale') || rawType.includes('sell') ? 'sell' : rawType.includes('purchase') || rawType.includes('buy') ? 'buy' : rawType || 'trade';
  const amount = x?.amount_range || x?.amount || x?.range || '—';
  return {
    ticker,
    representative: x?.member || x?.representative || x?.politician || x?.name || 'Membro do Congresso',
    chamber: String(x?.chamber || '').toLowerCase(),
    state: x?.state || '',
    type,
    amount,
    amount_range: amount,
    transaction_date: x?.transaction_date || x?.date || x?.trade_date || '',
    disclosure_date: x?.disclosure_date || x?.filed_date || x?.filing_date || '',
  };
}

async function fetchCongressTrades(ticker, limit = 100) {
  const tk = String(ticker || '').trim().toUpperCase().split('.')[0];
  const lim = Math.max(1, Math.min(100, Number(limit) || 100));
  const from = new Date(Date.now() - 120 * 86400000).toISOString().slice(0,10);
  const headers = {
    'User-Agent': 'Mozilla/5.0 Vestra/3.0',
    'Accept': 'application/json,text/plain,*/*'
  };
  const urls = [];
  // Current documented endpoint: global feed with ticker query.
  const q = new URL('https://www.bargo.ai/free-apis/congress/v1/trades');
  if (tk) q.searchParams.set('ticker', tk);
  q.searchParams.set('from', from);
  q.searchParams.set('limit', String(lim));
  urls.push(q.toString());
  // Compatibility fallback for the older per-ticker route.
  if (tk) urls.push(`https://www.bargo.ai/free-apis/congress/v1/trades/${encodeURIComponent(tk)}?from=${from}&limit=${lim}`);

  let lastStatus = null;
  for (const endpoint of urls) {
    try {
      const resp = await fetch(endpoint, { headers, cf: { cacheTtl: 900, cacheEverything: false } });
      lastStatus = resp.status;
      if (!resp.ok) continue;
      const payload = await resp.json();
      const raw = Array.isArray(payload) ? payload : (Array.isArray(payload?.trades) ? payload.trades : Array.isArray(payload?.data) ? payload.data : []);
      const trades = raw.map(normalizeCongressTrade).filter(x => x.ticker && (!tk || x.ticker === tk));
      return { trades: trades.slice(0, lim), source: 'Bargo Congress API', updated: new Date().toISOString() };
    } catch (_) {}
  }
  throw new Error(`Congress feed indisponível${lastStatus ? ` (${lastStatus})` : ''}`);
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin") || "";
    const cors = corsHeaders(origin);

    if (request.method === "OPTIONS")
      return new Response(null, { status: 204, headers: cors });
    if (request.method !== "GET")
      return new Response(JSON.stringify({ error: "Método não suportado" }),
        { status: 405, headers: { ...cors, "Content-Type": "application/json" } });

    try {
      if (url.pathname === "/quote") {
        const ticker = url.searchParams.get("ticker");
        if (!ticker) return new Response(JSON.stringify({ error: "ticker obrigatório" }),
          { status: 400, headers: { ...cors, "Content-Type": "application/json" } });
        const data = await fetchYahooQuote(ticker.trim().toUpperCase(), ctx);
        return new Response(JSON.stringify(data),
          { headers: { ...cors, "Content-Type": "application/json" } });
      }

      if (url.pathname === "/market") {
        const ticker = url.searchParams.get("ticker");
        if (!ticker) return new Response(JSON.stringify({ error: "ticker obrigatório" }),
          { status: 400, headers: { ...cors, "Content-Type": "application/json" } });
        const data = await fetchYahooMarketDetail(ticker.trim().toUpperCase(), ctx);
        return new Response(JSON.stringify(data),
          { headers: { ...cors, "Content-Type": "application/json" } });
      }

      if (url.pathname === "/congress") {
        const ticker = url.searchParams.get("ticker") || "";
        const limit = url.searchParams.get("limit") || "100";
        const data = await fetchCongressTrades(ticker, limit);
        return new Response(JSON.stringify(data),
          { headers: { ...cors, "Content-Type": "application/json", "Cache-Control": "public, max-age=300" } });
      }

      if (url.pathname === "/quotes") {
        const tickers = (url.searchParams.get("tickers") || "")
          .split(",").map(t => t.trim().toUpperCase()).filter(Boolean).slice(0, 20);
        if (!tickers.length) return new Response(JSON.stringify({ error: "tickers obrigatório" }),
          { status: 400, headers: { ...cors, "Content-Type": "application/json" } });
        const results = await Promise.allSettled(tickers.map(t => fetchYahooQuote(t, ctx)));
        const out = {};
        results.forEach((r, i) => {
          out[tickers[i]] = r.status === "fulfilled" ? r.value
            : { ticker: tickers[i], error: r.reason?.message || "Erro" };
        });
        return new Response(JSON.stringify(out),
          { headers: { ...cors, "Content-Type": "application/json" } });
      }

      if (url.pathname === "/" || url.pathname === "") {
        return new Response(JSON.stringify({
          service: "Vestra Market Proxy v4.2",
          endpoints: ["/quote?ticker=VWCE.DE", "/quotes?tickers=VWCE.DE,IWDA.L", "/market?ticker=MSFT", "/congress?ticker=NVDA", "/congress?limit=100"]
        }), { headers: { ...cors, "Content-Type": "application/json" } });
      }

      return new Response(JSON.stringify({ error: "Endpoint não encontrado" }),
        { status: 404, headers: { ...cors, "Content-Type": "application/json" } });

    } catch(e) {
      return new Response(JSON.stringify({ error: e.message || "Erro interno" }),
        { status: 500, headers: { ...cors, "Content-Type": "application/json" } });
    }
  },
};
