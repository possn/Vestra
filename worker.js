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
  const allowed = !origin || origin.includes("github.io") ||
    origin.includes("pages.dev") || origin.includes("localhost");
  return {
    "Access-Control-Allow-Origin": allowed ? (origin || "*") : "null",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
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
  const cacheKey = `quote31:${ticker.toUpperCase()}`;
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

async function fetchYahooMarketDetail(ticker, ctx) {
  const canonical = normalizeInputTicker(ticker);
  const cache = caches.default;
  const cacheUrl = `https://cache.internal/market40:${canonical}`;
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
    market_cap: Number.isFinite(marketCap) ? marketCap : null,
    trailing_pe: Number(raw(sd.trailingPE) ?? raw(ks.trailingPE)),
    forward_pe: Number(raw(sd.forwardPE) ?? raw(ks.forwardPE)),
    price_to_book: Number(raw(ks.priceToBook)),
    enterprise_to_ebitda: Number(raw(ks.enterpriseToEbitda)),
    dividend_yield: pctRaw(sd.dividendYield),
    roe: pctRaw(fd.returnOnEquity),
    roa: pctRaw(fd.returnOnAssets),
    revenue_growth: pctRaw(fd.revenueGrowth),
    earnings_growth: pctRaw(fd.earningsGrowth),
    profit_margin: pctRaw(fd.profitMargins),
    operating_margin: pctRaw(fd.operatingMargins),
    gross_margin: pctRaw(fd.grossMargins),
    free_cash_flow: Number.isFinite(fcf) ? fcf : null,
    fcf_yield: Number.isFinite(fcf) && Number.isFinite(marketCap) && marketCap > 0 ? (fcf / marketCap) * 100 : null,
    debt_to_equity: Number(raw(fd.debtToEquity)),
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
    price_history_1y: history,
    updated: new Date().toISOString(),
    source: qs ? 'Yahoo Finance quoteSummary + chart' : 'Yahoo Finance quote/chart'
  };
  for (const k of Object.keys(result)) if (typeof result[k] === 'number' && !Number.isFinite(result[k])) result[k] = null;
  ctx.waitUntil(cache.put(cacheUrl, new Response(JSON.stringify(result), {
    headers: { "Content-Type": "application/json", "Cache-Control": "public, max-age=300" }
  })));
  return result;
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
          service: "Vestra Market Proxy v4.0",
          endpoints: ["/quote?ticker=VWCE.DE", "/quotes?tickers=VWCE.DE,IWDA.L", "/market?ticker=MSFT"]
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
