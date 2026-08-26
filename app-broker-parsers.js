/* Vestra broker parsers v1.0 — file/row transformation only. */
(() => {
  'use strict';

  const { uid, isoToday, normalizeDate, normStr } = window.VestraUtils || {};
  const { normalizeRow, parseNumberSmart } = window.VestraFileParsing || {};
  const {
    normalizeISIN, brokerPositionClassFromTicker, brokerEventKey, brokerPositionKey,
    detectBrokerRowsFormat, detectBrokerTextFormat,
  } = window.VestraBrokerParsingCore || {};
  const { parseXTBNormalizeAction, xtbTickerToYahoo, xtbSymbolCurrency } = window.VestraXtbNormalization || {};

  if (![uid, isoToday, normalizeDate, normStr, normalizeRow, parseNumberSmart,
        normalizeISIN, brokerPositionClassFromTicker, brokerEventKey, brokerPositionKey,
        detectBrokerRowsFormat, detectBrokerTextFormat, parseXTBNormalizeAction,
        xtbTickerToYahoo, xtbSymbolCurrency].every(fn => typeof fn === 'function')) {
    throw new Error('Broker parser dependencies were not loaded before app-broker-parsers.js');
  }

function estimateEURFactorFromRow(r, grossLocal, totalEUR, ccy) {
  const cur = String(ccy || "EUR").toUpperCase();
  if (!cur || cur === "EUR") return 1;
  // v63: T212 exports an exact "Exchange rate" column — use it first.
  // Deriving totalEUR/grossLocal is imprecise because Total is rounded to 2dp
  // (e.g. gives 0.859057 instead of the true 0.853191).
  const fx = parseNumberSmart(r.exchange_rate);
  if (Number.isFinite(fx) && fx > 0 && fx < 10) return fx;
  if (grossLocal > 0 && totalEUR > 0) return totalEUR / grossLocal;
  return brokerApproxFxToEUR(cur);
}

function parseBrokerLedgerRows(rows, meta) {
  const events = [];
  for (const raw of (rows || [])) {
    const r = normalizeRow(raw);
    const type = normalizeBrokerAction(r.action);
    if (type === "OTHER") continue;
    const qty = parseNumberSmart(r.no_of_shares || r.quantity || r.qty || r.shares);
    const price = parseNumberSmart(r.price_share || r.price || r.price_per_share);
    const totalEUR = parseNumberSmart(r.total);
    const grossLocal = (Number.isFinite(qty) ? qty : 0) * (Number.isFinite(price) ? price : 0);
    const ccy = String(r.currency_price_share || r.currency || "EUR").trim().toUpperCase() || "EUR";
    const factor = estimateEURFactorFromRow(r, grossLocal, totalEUR, ccy);
    const taxLocal = parseNumberSmart(r.withholding_tax);
    const taxEUR = Number.isFinite(taxLocal) && taxLocal > 0 ? taxLocal * factor : 0;
    const feeEUR = [r.currency_conversion_fee, r.stamp_duty_reserve_tax, r.french_transaction_tax]
      .map(parseNumberSmart)
      .filter(v => Number.isFinite(v) && v > 0)
      .reduce((a, b) => a + b, 0);
    const when = String(r.time || r.time_utc || r.date || r.record_date || "").trim();
    const date = normalizeDate(when.slice(0, 10)) || normalizeDate(when) || isoToday();
    const evt = {
      id: uid(),
      sourceHash: meta.hash,
      sourceName: meta.name,
      broker: meta.broker,
      type,
      actionRaw: String(r.action || "").trim(),
      date,
      dateTime: when || date,
      isin: String(r.isin || "").trim(),
      ticker: String(r.ticker || r.symbol || "").trim(),
      name: String(r.name || r.instrument || "").trim(),
      notes: String(r.notes || "").trim(),
      qty: Number.isFinite(qty) ? qty : 0,
      pricePerShare: Number.isFinite(price) ? price : 0,
      totalEUR: Number.isFinite(totalEUR) ? totalEUR : 0,
      totalCurrency: String(r.currency_total || "EUR").trim().toUpperCase() || "EUR",
      grossLocal: Number.isFinite(grossLocal) ? grossLocal : 0,
      localCurrency: ccy,
      taxEUR,
      feeEUR,
      resultEUR: parseNumberSmart(r.result),
      key: ""
    };
    evt.key = brokerEventKey(evt);
    events.push(evt);
  }
  return events;
}

function parseBrokerPositionRows(rows, meta) {
  const positions = [];
  for (const raw of (rows || [])) {
    const r = normalizeRow(raw);
    const ticker = String(r.ticker || r.symbol || "").trim();
    const qty = parseNumberSmart(r.quantity || r.qty || r.shares || r.no_of_shares || r.units);
    const cps = parseNumberSmart(r.cost_per_share || r.price_share || r.price || r.preco);
    if ((!ticker && !normalizeISIN(r.isin)) || !Number.isFinite(qty) || !Number.isFinite(cps) || qty <= 0) continue;
    const ccy = String(r.currency || r.ccy || r.currency_price_share || "EUR").trim().toUpperCase() || "EUR";
    const costBasisEUR = qty * cps * brokerApproxFxToEUR(ccy);
    const pos = {
      id: uid(),
      sourceHash: meta.hash,
      sourceName: meta.name,
      broker: meta.broker,
      ticker,
      isin: normalizeISIN(r.isin),
      name: String(r.name || r.security || ticker || r.isin).trim(),
      qty,
      costBasisEUR,
      marketValueEUR: parseNumberSmart(r.market_value || r.market_value_eur || r.valor_mercado_eur) || 0,
      pricePerShare: cps,
      priceCurrency: ccy,
      class: brokerPositionClassFromTicker(ticker),
      positionKind: "cost_snapshot",
      snapshotDate: normalizeDate(r.date || r.as_of || meta.asOfDate || "") || "",
      key: ""
    };
    pos.key = brokerPositionKey(pos);
    positions.push(pos);
  }
  return positions;
}

function parseXTBTradesRows(rows, meta) {
  const events = [];
  for (const raw of (rows || [])) {
    const r = normalizeRow(raw);
    const symbol   = String(r.symbol || r.simbolo || r.instrumento || r.ticker || "").trim();
    const typeRaw  = String(r.type || r.tipo || r.direction || r.direcao || "").trim();
    const openTime = String(r.open_time || r.opentime || r.hora_de_abertura || r.hora_abertura ||
                             r.data_de_abertura || r.data_abertura || r.abertura || "").trim();
    const closeTime= String(r.close_time || r.closetime || r.hora_de_fecho || r.hora_fecho ||
                            r.data_de_fecho || r.data_fecho || r.fecho || "").trim();
    const openPx   = parseNumberSmart(r.open_price || r.openprice || r.preco_de_abertura || r.preco_abertura || r.preco_entrada);
    const closePx  = parseNumberSmart(r.close_price || r.closeprice || r.preco_de_fecho || r.preco_fecho || r.preco_saida);
    const vol      = parseNumberSmart(r.volume || r.qty || r.quantity || r.quantidade || r.units);
    const profit   = parseNumberSmart(r.profit || r.lucro || r.resultado || r.pl || r.profit_loss || r.gross_p_l || r.gross_pl);
    const commission = parseNumberSmart(r.commission || r.comissao || r.comissoes || 0);
    const swap     = parseNumberSmart(r.swap || r.swap_points || 0);
    const purchaseValue = parseNumberSmart(r.purchase_value || r["purchase value"] || r.valor_de_compra || r.valor_compra);
    const saleValue = parseNumberSmart(r.sale_value || r["sale value"] || r.valor_de_venda || r.valor_venda);
    const comment  = String(r.comment || r.comentario || r.comments || r.descricao || "").trim();

    if (!symbol || !Number.isFinite(vol) || vol <= 0) continue;

    const dateStr = normalizeDate((closeTime || openTime || "").slice(0, 10)) || isoToday();
    const ticker  = xtbTickerToYahoo(symbol);
    const ccy = xtbSymbolCurrency(symbol);
    const fx = brokerApproxFxToEUR(ccy);
    const pricePerShare = Number.isFinite(closePx) && closePx > 0 ? closePx : openPx;
    const swapCost = Number.isFinite(swap) && swap < 0 ? Math.abs(swap) : 0;
    const feeEUR   = Math.abs(commission) + swapCost;
    // XTB: purchase_value and sale_value are in account currency (EUR) — do NOT apply fx
    // Only apply fx when computing from price×qty (native currency)
    const costEUR  = Number.isFinite(purchaseValue) && purchaseValue > 0
      ? purchaseValue  // already in EUR
      : vol * (Number.isFinite(openPx) && openPx > 0 ? openPx : pricePerShare) * fx;
    const proceedsEUR = Number.isFinite(saleValue) && saleValue > 0
      ? saleValue  // already in EUR
      : vol * (Number.isFinite(closePx) && closePx > 0 ? closePx : pricePerShare) * fx;
    // Prefer broker-reported Gross P/L; fallback to computed
    const pnlEUR = Number.isFinite(profit) && profit !== 0 ? profit : (proceedsEUR - costEUR - feeEUR);

    const evt = {
      id: uid(), sourceHash: meta.hash, sourceName: meta.name, broker: "XTB",
      type: "REALIZED_TRADE", actionRaw: typeRaw || "Closed position",
      date: dateStr, dateTime: closeTime || dateStr,
      ticker, isin: "", name: symbol,
      qty: vol,
      pricePerShare: Number.isFinite(pricePerShare) ? pricePerShare : 0,
      totalEUR: proceedsEUR,
      totalCurrency: "EUR",
      grossLocal: Number.isFinite(saleValue) && saleValue > 0 ? saleValue : vol * (Number.isFinite(closePx) && closePx > 0 ? closePx : pricePerShare),
      localCurrency: ccy,
      taxEUR: 0, feeEUR,
      costBasisEUR: costEUR,
      resultEUR: pnlEUR,
      notes: comment, key: ""
    };
    evt.key = brokerEventKey(evt);
    events.push(evt);
  }
  return events;
}

function parseXTBPositionsRows(rows, meta) {
  // XTB exports one row per buy lot — aggregate all lots per ticker into one position
  const lotMap = new Map(); // key: symbol → aggregated lot data
  for (const raw of (rows || [])) {
    const r = normalizeRow(raw);
    const symbol   = String(r.symbol || r.simbolo || r.instrumento || "").trim();
    const vol      = parseNumberSmart(r.volume || r.qty || r.quantity);
    const openPx   = parseNumberSmart(r.open_price || r["open price"] || r.openprice || r.preco_de_abertura || r.preco_abertura || r.preco_entrada);
    const mktPx    = parseNumberSmart(r.market_price || r["market price"] || r.marketprice || r["current price"] || r.preco_atual || r.preco_de_mercado);
    const purchaseValue = parseNumberSmart(r.purchase_value || r["purchase value"] || r.valor_de_compra || r.valor_compra);

    if (!symbol || !Number.isFinite(vol) || vol <= 0) continue;
    const nativeCcy = xtbSymbolCurrency(symbol);
    const fx = brokerApproxFxToEUR(nativeCcy);
    const usePrice = Number.isFinite(mktPx) && mktPx > 0 ? mktPx : (Number.isFinite(openPx) ? openPx : 0);
    const hasPV = Number.isFinite(purchaseValue) && purchaseValue > 0;
    const lotCost = hasPV ? purchaseValue : vol * (Number.isFinite(openPx) && openPx > 0 ? openPx : usePrice) * fx;
    let lotMktVal;
    if (hasPV && Number.isFinite(openPx) && openPx > 0 && Number.isFinite(usePrice) && usePrice > 0) {
      lotMktVal = purchaseValue * (usePrice / openPx);
    } else {
      lotMktVal = vol * usePrice * fx;
    }

    if (!lotMap.has(symbol)) {
      lotMap.set(symbol, { symbol, totalQty: 0, totalCost: 0, totalMktVal: 0, lastMktPx: 0, nativeCcy });
    }
    const agg = lotMap.get(symbol);
    agg.totalQty   += vol;
    agg.totalCost  += lotCost;
    agg.totalMktVal += lotMktVal;
    if (usePrice > 0) agg.lastMktPx = usePrice; // keep last known market price
  }

  const positions = [];
  for (const agg of lotMap.values()) {
    const ticker = xtbTickerToYahoo(agg.symbol);
    const avgPx  = agg.totalQty > 0 ? agg.lastMktPx : 0;
    const pos = {
      id: uid(), sourceHash: meta.hash, sourceName: meta.name, broker: "XTB",
      ticker, isin: "", name: agg.symbol,
      qty: agg.totalQty, costBasisEUR: agg.totalCost, marketValueEUR: agg.totalMktVal,
      pricePerShare: avgPx, priceCurrency: agg.nativeCcy,
      class: brokerPositionClassFromTicker(ticker),
      positionKind: "market_snapshot",
      snapshotDate: meta.asOfDate || isoToday(),
      key: ""
    };
    pos.key = brokerPositionKey(pos);
    positions.push(pos);
  }
  return positions;
}

function parseXTBCashRows(rows, meta) {
  const events = [];
  for (const raw of (rows || [])) {
    const r = normalizeRow(raw);
    const typeRaw = String(r.tipo || r.type || r.tipo_de_operacao || r.tipo_operacao || r.descricao_tipo || "").trim();
    const symbol  = String(r.simbolo || r.symbol || r.ticker || r.instrumento || r.ativo || "").trim();
    const amount  = parseNumberSmart(r.montante || r.amount || r.valor || r.lucro || r.profit || r.resultado);
    const comment = String(r.comentario || r.comment || r.comments || r.descricao || r.observacoes || "").trim();
    const dateRaw = String(r.data || r.date || r.datetime || r.time || r.hora || r.data_operacao || "").trim();
    // v63b: XTB's unique per-row transaction ID — required to keep same-second lots distinct
    const extId = String(r.id || r.id_transacao || r.transaction_id || "").trim();

    if (!Number.isFinite(amount) || amount === 0) continue;
    let type = parseXTBNormalizeAction(typeRaw, comment);
    if (type === "OTHER") continue;
    const dateStr = normalizeDate(dateRaw.slice(0, 10)) || normalizeDate(dateRaw) || isoToday();
    const ticker  = symbol ? xtbTickerToYahoo(symbol) : "";
    const evt = {
      id: uid(), sourceHash: meta.hash, sourceName: meta.name, broker: "XTB",
      extId,
      type, actionRaw: typeRaw,
      date: dateStr, dateTime: dateRaw || dateStr,
      ticker,
      yahooTicker: ticker, // explicitly set so merge logic works regardless of currency
      isin: "",
      name: (r.instrumento || r.instrument || r.name_col || r.nm || "").trim() || symbol || typeRaw,
      qty: 0, pricePerShare: 0,
      totalEUR: Math.abs(amount), totalCurrency: "EUR",
      grossLocal: Math.abs(amount), localCurrency: "EUR",
      taxEUR: 0, feeEUR: 0, resultEUR: amount,
      notes: comment, key: ""
    };
    // v63: XTB posts dividend REVERSALS as negative "Dividend" rows (comment
    // starts with "corr ..."). Math.abs() flipped them positive, inflating gross
    // by 2x the correction (verified: 21 rows, +20.74 EUR). Keep the sign.
    if (type === "DIVIDEND" && amount < 0) {
      evt.type = "DIVIDEND_ADJ";
      evt.totalEUR = amount;      // negative
      evt.grossLocal = amount;
      evt.resultEUR = amount;
    }
    // Handle Stock purchase / Stock sale with qty from comment
    if (type === "XTB_STOCK_PURCHASE" || type === "XTB_STOCK_SALE") {
      // Extract qty from comment: "OPEN BUY 2/4 @ 63.38" or "CLOSE BUY 1 @ 13.00"
      const qtyMatch = comment.match(/(?:OPEN|CLOSE)\s+(?:BUY|SELL)\s+(\d+(?:\.\d+)?)(?:\/\d+)?\s*@\s*([\d.]+)/i);
      const qty  = qtyMatch ? parseFloat(qtyMatch[1]) : 0;
      const price = qtyMatch ? parseFloat(qtyMatch[2]) : 0;
      evt.qty = qty;
      evt.pricePerShare = price;
      evt.totalEUR = Math.abs(amount);
      evt.type = type === "XTB_STOCK_PURCHASE" ? "BUY" : "SELL";
      if (type === "XTB_STOCK_SALE") {
        evt.resultEUR = amount;
      }
      if (!qty || qty <= 0) continue;
      // NGAS.UK is a leveraged ETC where XTB's internal lot units are incompatible
      // with Yahoo Finance's price units — skip entirely from Cash Ops reconstruction.
      // The correct position comes from the OPEN POSITION sheet (parseXTBPositionRows).
      if (symbol && symbol.toUpperCase() === "NGAS.UK") continue;
    }
    if (type === "DIVIDEND_TAX") {
      evt.type = "DIVIDEND_ADJ";
      evt.totalEUR = 0;
      evt.grossLocal = 0;
      evt.taxEUR = Math.abs(amount);
      evt.resultEUR = -Math.abs(amount);
    } else if (type === "CASH_INTEREST_TAX") {
      evt.type = "WITHDRAWAL";
      evt.totalEUR = Math.abs(amount);
      evt.grossLocal = Math.abs(amount);
      evt.resultEUR = -Math.abs(amount);
    }
    evt.key = brokerEventKey(evt);
    events.push(evt);
  }
  return events;
}

async function parseBrokerImportFile(file) {
  const name = String(file?.name || "").toLowerCase();
  if (name.endsWith(".pdf")) {
    const text = await extractTextFromPDF(file);
    const format = detectBrokerTextFormat(text);
    return { format, text, rows: [], textLength: text.length };
  }
  if (name.endsWith(".xlsx") || name.endsWith(".xls")) {
    if (typeof XLSX === "undefined") throw new Error("Biblioteca Excel não carregada.");
    const ab = await file.arrayBuffer();
    const wb = XLSX.read(ab, { type: "array", raw: false, cellDates: true });
    const blocks = workbookToBrokerBlocks(wb);
    if (blocks.length > 1) return { format: "workbook_multi", rows: [], text: "", blocks };
    if (blocks.length === 1) return { format: blocks[0].format, rows: blocks[0].rows, text: "", blocks };
  }
  const rows = await fileToObjectRows(file);
  const format = detectBrokerRowsFormat(rows);
  return { format, rows, text: "" };
}

function parseTrading212HoldingsPdf(text, meta) {
  const rawText = String(text || "");
  const lines = rawText
    .split(/\r?\n/)
    .map(s => String(s || "").replace(/	+/g, " ").replace(/\s+/g, " ").trim())
    .filter(Boolean);

  const totalMatch = rawText.match(/Valor dos ativos:\s*([0-9.,]+)\s*EUR/i);
  const asOfMatch = rawText.match(/as of\s+(\d{2}\/\d{2}\/\d{4})/i);
  meta.snapshotTotalEUR = totalMatch ? parseNumberSmart(totalMatch[1]) : 0;
  meta.asOfDate = asOfMatch ? normalizeDate(asOfMatch[1]) : "";

  const positions = [];
  const seen = new Set();
  const ignore = (s) => {
    const n = normStr(s || "");
    return !n || n === "instrument" || n === "isin" || n === "quantity" || n === "price" ||
      n.includes("nif") || n.includes("id de cliente") || n.includes("nome do cliente") ||
      n.includes("confirmacao de ativos") || n.includes("trading 212 invest") || n.includes("trading 212 crypto") ||
      n.includes("valor dos ativos") || n.includes("este documento") || n.includes("a informacao aqui apresentada") ||
      n.includes("trading 212 e a denominacao") || n.includes("sem dados disponiveis") || /^\d+\/\d+$/.test(String(s || ""));
  };
  const rowRe = /^(.*?)\s+([A-Z]{2}[A-Z0-9]{9}\d)\s+([0-9][0-9.,]*)\s+([A-Z]{3})\s+([0-9][0-9.,]*)$/;
  const pushPos = (name, isin, qtyLine, priceLine) => {
    const isinNorm = normalizeISIN(isin);
    const qty = parseNumberSmart(qtyLine);
    const m = String(priceLine || "").match(/^([A-Z]{3})\s+([0-9][0-9.,]*)$/);
    if (!isinNorm || !Number.isFinite(qty) || qty <= 0 || !m) return false;
    const ccy = String(m[1] || "EUR").toUpperCase();
    const px = parseNumberSmart(m[2]);
    if (!Number.isFinite(px)) return false;
    const pos = {
      id: uid(),
      sourceHash: meta.hash,
      sourceName: meta.name,
      broker: meta.broker,
      ticker: "",
      isin: isinNorm,
      name: String(name || isinNorm).trim(),
      qty,
      costBasisEUR: 0,
      marketValueEUR: qty * px * brokerApproxFxToEUR(ccy),
      pricePerShare: px,
      priceCurrency: ccy,
      class: "Ações/ETFs",
      positionKind: "market_snapshot",
      snapshotDate: meta.asOfDate || "",
      key: ""
    };
    pos.key = brokerPositionKey(pos);
    if (seen.has(pos.key)) return false;
    seen.add(pos.key);
    positions.push(pos);
    return true;
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (ignore(line)) continue;
    const m = line.match(rowRe);
    if (m) {
      pushPos(m[1], m[2], m[3], `${m[4]} ${m[5]}`);
      continue;
    }
    const isin = normalizeISIN(line);
    if (!isin) continue;
    let j = i - 1;
    while (j >= 0 && ignore(lines[j])) j -= 1;
    let k = i + 1;
    while (k < lines.length && ignore(lines[k])) k += 1;
    let l = k + 1;
    while (l < lines.length && ignore(lines[l])) l += 1;
    if (j >= 0 && k < lines.length && l < lines.length) {
      pushPos(lines[j], isin, lines[k], lines[l]);
    }
  }
  const parsedTotal = positions.reduce((s, p) => s + Math.max(0, parseNum(p.marketValueEUR)), 0);
  if (meta.snapshotTotalEUR > 0 && parsedTotal > 0) {
    const scale = meta.snapshotTotalEUR / parsedTotal;
    if (Math.abs(scale - 1) > 0.001) {
      positions.forEach(p => { p.marketValueEUR = Math.max(0, parseNum(p.marketValueEUR)) * scale; p.key = brokerPositionKey(p); });
    }
  }
  return positions;
}

  window.VestraBrokerParsers = Object.freeze({
    estimateEURFactorFromRow,
    parseBrokerLedgerRows,
    parseBrokerPositionRows,
    parseXTBTradesRows,
    parseXTBPositionsRows,
    parseXTBCashRows,
    parseBrokerImportFile,
    parseTrading212HoldingsPdf,
  });
})();
