/* Vestra broker parsing core v1.0 — pure identity, format and key helpers. */
(() => {
  'use strict';

  const { normStr, parseNum } = window.VestraUtils || {};
  const { ISIN_YAHOO_MAP } = window.VestraAssetIdentity || {};
  if (typeof normStr !== 'function' || typeof parseNum !== 'function') {
    throw new Error('VestraUtils não foi carregado antes de app-broker-parsing-core.js');
  }
  if (!ISIN_YAHOO_MAP || typeof ISIN_YAHOO_MAP !== 'object') {
    throw new Error('VestraAssetIdentity não foi carregado antes de app-broker-parsing-core.js');
  }

function normalizeISIN(v) {
  const s = String(v || "").trim().toUpperCase();
  return /^[A-Z]{2}[A-Z0-9]{9}\d$/.test(s) ? s : "";
}

function normalizeSecurityNameKey(v) {
  return String(v || "")
    .toUpperCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/\b(INC|INCORPORATED|CORP|CORPORATION|CO|COMPANY|SA|S A|SGPS|PLC|LTD|LIMITED|NV|N V|AG|SE|ETF|ETFS|FUND|FUNDO|CLASS [A-Z]|ORDINARY SHARES|SHARES)\b/g, " ")
    .replace(/[^A-Z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

const KNOWN_BROKER_YAHOO_OVERRIDES = {
  "AT0000A3EPA4|AMS": "AMS.SW",
  "AU0000185993|IREN": "IREN",
  "BRVALEACNOR0|XVALO": "XVALO.MC",
  "CH0334081137|CRSP": "CRSP",
  "GB0007188757|RIO1": "RIO.L",
  "GB00BVZK7T90|UNA": "UNA.AS",
  "IE00045C7B38|HTOO": "HTOO",
  "IE00BLS09M33|PNR": "PNR",
  "IE00BTN1Y115|MDT": "MDT",
  "IE00BY7QL619|JCI": "JCI",
  "IT0003128367|ENL": "ENEL.MI",
  "NL0009434992|LYB": "LYB",
  "NL0009805522|NBIS": "NBIS",
  "NL00150001Q9|STLA": "STLA",
  "AT0000A3EPA4|AMS-OSRAM": "AMS.SW",
  "|MPW.US": "MPT",
  "|CRSP": "CRSP",
  "|NZYMB.DK": "NSIS-B.CO",
  "|STM.FR": "STMPA.PA",
  "|RIO1": "RIO.L",
  "|UNA": "UNA.AS",
  "|ENL": "ENEL.MI",
  "|XVALO": "XVALO.MC"
};

function getKnownBrokerYahooOverride({ isin = "", ticker = "", name = "", currency = "", priceCurrency = "" } = {}) {
  const i = String(isin || "").trim().toUpperCase();
  const t = String(ticker || "").trim().toUpperCase();
  const n = normalizeSecurityNameKey(name || "");
  const ccy = String(priceCurrency || currency || "").trim().toUpperCase();
  const pair = `${i}|${t}`;
  if (KNOWN_BROKER_YAHOO_OVERRIDES[pair]) return KNOWN_BROKER_YAHOO_OVERRIDES[pair];
  if (KNOWN_BROKER_YAHOO_OVERRIDES[`|${t}`]) return KNOWN_BROKER_YAHOO_OVERRIDES[`|${t}`];

  if (t === "STM.FR" || /\bSTMICROELECTRONICS\b/.test(n)) return "STMPA.PA";
  if (t === "NZYMB.DK" || /\bNOVOZYMES\b/.test(n)) return "NSIS-B.CO";
  if ((t === "AMS" || /\bAMS[ -]OSRAM\b/.test(n)) && (ccy === "CHF" || i === "AT0000A3EPA4")) return "AMS.SW";
  if ((t === "EDV" || /\bENDEAVOUR MINING\b/.test(n)) && ccy === "CAD") return "EDV.TO";
  if ((t === "NEO" || /\bNEO PERFORMANCE MATERIALS\b/.test(n)) && ccy === "CAD") return "NEO.TO";
  if ((t === "XVALO" || /\bVALE\b/.test(n)) && i === "BRVALEACNOR0") return "XVALO.MC";
  if ((t === "UNA" || /\bUNILEVER\b/.test(n)) && i === "GB00BVZK7T90") return "UNA.AS";
  if ((t === "RIO1" || /\bRIO TINTO\b/.test(n)) && i === "GB0007188757") return "RIO.L";
  if ((t === "NBIS" || /\bNEBIUS\b/.test(n)) && i === "NL0009805522") return "NBIS";
  if ((t === "STLA" || /\bSTELLANTIS\b/.test(n)) && i === "NL00150001Q9") return "STLA";
  if ((t === "PNR" || /\bPENTAIR\b/.test(n)) && i === "IE00BLS09M33") return "PNR";
  if ((t === "LYB" || /\bLYONDELLBASELL\b/.test(n)) && i === "NL0009434992") return "LYB";
  if ((t === "JCI" || /\bJOHNSON CONTROLS\b/.test(n)) && i === "IE00BY7QL619") return "JCI";
  if ((t === "MDT" || /\bMEDTRONIC\b/.test(n)) && i === "IE00BTN1Y115") return "MDT";
  if ((t === "CRSP" || /\bCRISPR THERAPEUTICS\b/.test(n)) && i === "CH0334081137") return "CRSP";
  if ((t === "IREN" || n === "IREN") && i === "AU0000185993") return "IREN";
  if ((t === "ENL" || /\bENEL\b/.test(n)) && i === "IT0003128367") return "ENEL.MI";
  if ((t === "HTOO" || /\bFUSION FUEL GREEN\b/.test(n)) && i === "IE00045C7B38") return "HTOO";
  if (t === "MPW.US" || t === "MPW" || /\bMEDICAL PROPERTIES TRUST\b/.test(n)) return "MPT";
  return "";
}

function canonicalBrokerTickerBase(v) {
  let t = String(v || "").trim().toUpperCase();
  if (!t) return "";
  t = t.normalize("NFD").replace(/[̀-ͯ]/g, "");
  if (/^[A-Z0-9.-]+\.US$/.test(t)) return t.replace(/\.US$/, "");
  if (/^[A-Z0-9.-]+\.(NYSE|NASDAQ|XNAS|XNYS|ARCA|AMEX)$/.test(t)) return t.replace(/\.(NYSE|NASDAQ|XNAS|XNYS|ARCA|AMEX)$/, "");
  // Strip exchange suffixes: .SW, .DE, .L, .PA, .AS, .MC, .MI, .TO, .CO, .ST, .LS, .HE, .BR, .AX, .F, .VI, .WA, .OL
  const exSuffix = t.match(/^([A-Z0-9]+)\.(SW|DE|L|PA|AS|MC|MI|TO|CO|ST|LS|HE|BR|AX|F|VI|WA|OL|SG|IR)$/);
  if (exSuffix) return exSuffix[1];
  return t;
}

function inferPreferredVenueTicker(rawTicker = "", venue = "") {
  const t = String(rawTicker || "").trim().toUpperCase();
  const v = String(venue || "").trim().toUpperCase();
  if (!t || !v || /[=\-]/.test(t) || t.includes(".")) return "";
  return `${t}.${v}`;
}

function venueFromIsinAndCurrency(isin = "", currency = "", name = "", rawTicker = "") {
  const prefix = String(isin || "").trim().toUpperCase().slice(0, 2);
  const ccy = String(currency || "").trim().toUpperCase();
  const nm = normalizeSecurityNameKey(name || "");
  const raw = String(rawTicker || "").trim().toUpperCase();
  const isAccFund = /\bACC\b/.test(nm) || /\bISHARES\b/.test(nm) || /\bXTRACKERS\b/.test(nm) ||
    /\bWISDOMTREE\b/.test(nm) || /\bVANECK\b/.test(nm) || /\bKRANESHARES\b/.test(nm) ||
    /\bGLOBAL X\b/.test(nm) || /\bETF\b/.test(nm) || /\bFUND\b/.test(nm);

  if (prefix === "PT") return "LS";
  if (prefix === "ES") return "MC";
  if (prefix === "FR") return "PA";
  if (prefix === "IT") return "MI";
  if (prefix === "DE") return "DE";
  if (prefix === "AT") return "VI";
  if (prefix === "CH") return "SW";
  if (prefix === "DK") return "CO";
  if (prefix === "SE") return "ST";
  if (prefix === "NO") return "OL";
  if (prefix === "FI") return "HE";
  if (prefix === "BE") return "BR";
  if (prefix === "GB") return "L";
  if (prefix === "AU") return "AX";
  if (prefix === "CA") return "TO";

  if (/\bAIRBUS\b/.test(nm)) return "PA";
  if (/\bARCELORMITTAL\b/.test(nm)) return "AS";

  if (prefix === "NL") {
    if (ccy === "USD" && raw && /^[A-Z0-9.-]{1,10}$/.test(raw) && !isAccFund) return "";
    return "AS";
  }
  if (prefix === "LU") {
    if (ccy === "USD" && raw && /^[A-Z0-9.-]{1,10}$/.test(raw) && !isAccFund) return "";
    if (/\bARCELORMITTAL\b/.test(nm) || raw === "MT") return "AS";
    return "LU";
  }
  if (prefix === "IE") {
    if (isAccFund) {
      if (ccy === "GBP" || ccy === "GBX" || ccy === "USD") return "L";
      if (ccy === "EUR" || !ccy) return "DE";
    }
    if (ccy === "USD" && raw && /^[A-Z0-9.-]{1,10}$/.test(raw)) return "";
    if (ccy === "GBP" || ccy === "GBX") return "L";
  }
  return "";
}

function inferYahooTickerFromIdentity({ isin = "", ticker = "", yahooTicker = "", name = "", currency = "", priceCurrency = "" } = {}) {
  const i = normalizeISIN(isin);
  const direct = String(yahooTicker || "").trim().toUpperCase();
  const t = String(ticker || "").trim().toUpperCase();
  const n = normalizeSecurityNameKey(name);
  const ccy = String(priceCurrency || currency || "").trim().toUpperCase();

  const knownOverride = getKnownBrokerYahooOverride({ isin: i, ticker: t, yahooTicker: direct, name, currency, priceCurrency });
  if (knownOverride) return String(knownOverride).trim().toUpperCase();

  if (direct) {
    if (/^[A-Z0-9.-]+\.US$/.test(direct)) return direct.replace(/\.US$/, "");
    if (/^[A-Z0-9.-]+\.CH$/.test(direct)) return direct.replace(/\.CH$/, ".SW");
    if (/^[A-Z0-9.-]+\.PT$/.test(direct)) return direct.replace(/\.PT$/, ".LS");
    if (/\.(LS|L|PA|AS|MC|SW|CO|ST|OL|HE|BR|MI|AX|TO|DE|F|VI|IR)$/.test(direct) || /[=\-]/.test(direct)) return direct;
    // Plain ticker already in Yahoo format (e.g. "O", "MSFT", "VWCE.DE") — return as-is
    if (/^[A-Z0-9]{1,6}$/.test(direct) || /^[A-Z0-9]{1,6}\.[A-Z]{1,2}$/.test(direct)) return direct;
  }

  if (/\bCORTICEIRA\b/.test(n) || /\bAMORIM\b/.test(n)) return "COR.LS";
  if (/\bSONAE\b/.test(n)) return "SON.LS";
  // Realty Income identified via ISIN US7561091049 → "O" in ISIN_YAHOO_MAP (see above)
  if (/\bAIRBUS\b/.test(n)) return "AIR.PA";
  if (/\bARCELORMITTAL\b/.test(n)) return "MT.AS";

  if (/^[A-Z0-9.-]+\.US$/.test(t)) return t.replace(/\.US$/, "");
  if (/^[A-Z0-9.-]+\.CH$/.test(t)) return t.replace(/\.CH$/, ".SW");
  if (/^[A-Z0-9.-]+\.PT$/.test(t)) return t.replace(/\.PT$/, ".LS");
  if (/^[A-Z0-9.-]+\.GB$/.test(t)) return t.replace(/\.GB$/, ".L");
  if (/^[A-Z0-9.-]+\.FR$/.test(t)) return t.replace(/\.FR$/, ".PA");
  if (/^[A-Z0-9.-]+\.NL$/.test(t)) return t.replace(/\.NL$/, ".AS");
  if (/^[A-Z0-9.-]+\.ES$/.test(t)) return t.replace(/\.ES$/, ".MC");
  if (/^[A-Z0-9.-]+\.DK$/.test(t)) return t.replace(/\.DK$/, ".CO");
  if (/\.(LS|L|PA|AS|MC|SW|CO|ST|OL|HE|BR|MI|AX|TO|DE|F|VI|IR)$/.test(t) || /[=\-]/.test(t)) return t;

  const rawPlain = canonicalBrokerTickerBase(t);
  const isAccFund = /\bACC\b/.test(n) || /\bETF\b/.test(n) || /\bFUND\b/.test(n) || /\bISHARES\b/.test(n) || /\bXTRACKERS\b/.test(n) || /\bWISDOMTREE\b/.test(n) || /\bVANECK\b/.test(n) || /\bGLOBAL X\b/.test(n) || /\bKRANESHARES\b/.test(n);
  if (rawPlain && /^[A-Z0-9.-]{1,10}$/.test(rawPlain) && ccy === "USD" && !isAccFund) return rawPlain;
  if (rawPlain && /^[A-Z0-9.-]{1,10}$/.test(rawPlain)) {
    const venue = venueFromIsinAndCurrency(i, ccy, n, rawPlain);
    if (venue) return inferPreferredVenueTicker(rawPlain, venue);
  }

  if (i && ISIN_YAHOO_MAP[i]) return String(ISIN_YAHOO_MAP[i] || "").trim().toUpperCase();

  return "";
}

function sameSecurityName(a, b) {
  const na = normalizeSecurityNameKey(a);
  const nb = normalizeSecurityNameKey(b);
  if (!na || !nb) return false;
  return na === nb || na.startsWith(nb) || nb.startsWith(na);
}

function sameBrokerSecurityIdentity(a, b) {
  const ia = normalizeISIN(a && a.isin);
  const ib = normalizeISIN(b && b.isin);
  if (ia && ib) return ia === ib;

  const ya = inferYahooTickerFromIdentity(a || {});
  const yb = inferYahooTickerFromIdentity(b || {});
  if (ya && yb && ya === yb) return true;

  const ta = canonicalBrokerTickerBase((a && (a.ticker || a.yahooTicker)) || "");
  const tb = canonicalBrokerTickerBase((b && (b.ticker || b.yahooTicker)) || "");
  if (ta && tb && ta === tb && sameSecurityName(a && a.name, b && b.name)) return true;

  if (sameSecurityName(a && a.name, b && b.name) && (!ta || !tb || ta === tb)) return true;
  return false;
}

function makeBrokerSecurityKey({ isin = "", ticker = "", name = "", currency = "", priceCurrency = "", totalCurrency = "", yahooTicker = "" } = {}) {
  const i = normalizeISIN(isin);
  if (i) return `ISIN:${i}`;
  const y = inferYahooTickerFromIdentity({ isin, ticker, yahooTicker, name });
  if (y) return `YAHOO:${y}`;
  const t = canonicalBrokerTickerBase(ticker || yahooTicker || "");
  const n = normalizeSecurityNameKey(name || "");
  const c = String(currency || priceCurrency || totalCurrency || "").trim().toUpperCase();
  if (t && n) return `TICKER_NAME:${t}|${n}`;
  if (t && c) return `TICKER_CCY:${t}|${c}`;
  if (t) return `TICKER:${t}`;
  return `NAME:${n}`;
}

function detectBrokerRowsFormat(rows) {
  if (!Array.isArray(rows) || !rows.length) return "unknown";
  const sample = rows.slice(0, 8).map(normalizeRow);
  const keys = new Set();
  sample.forEach(r => Object.keys(r || {}).forEach(k => keys.add(k)));
  const has = (...arr) => arr.some(k => keys.has(k));
  // Trading 212 ledger
  // v63p: T212 renamed the "Time" column to "Time (UTC)" in newer exports (seen in
  // 2026 CSVs). Because this check required exactly "time", a 2026 export fell
  // through to the next rule ("positions") — Action/ISIN/Ticker/No. of shares/
  // Price per share/Total are ALSO a superset match for a generic positions CSV.
  // The result: 1364 ledger rows (BUY/SELL/DIVIDEND events) were reinterpreted as
  // 1364 static cost-basis SNAPSHOTS, each holding the security's running quantity.
  // Those snapshot quantities were then summed on top of the real BUY/SELL events
  // from the OTHER T212 years, silently doubling holdings (e.g. ADM: 23 real buys
  // + a 23-share snapshot = 46, plus XTB's 15 = 61 instead of 38).
  if (has("action") && has("time", "time_utc") && has("ticker", "isin") && has("total")) return "broker_ledger";
  // Generic positions CSV (cost per share)
  if (has("ticker", "symbol") && has("quantity", "qty", "shares", "no_of_shares") && has("cost_per_share", "price_share", "price", "preco")) return "positions";
  // XTB trade history CSV (closed trades)
  // EN cols: Symbol,Type,Open time,Close time,Open price,Close price,Volume,Profit,Commission,Swap
  // PT cols (after normKey accent strip): simbolo,tipo,data_de_abertura,data_de_fecho,preco_de_abertura,preco_de_fecho,volume,lucro,comissao,swap
  const hasSymbolOrSimb = has("symbol","simbolo","instrumento");
  const hasOpenTime  = has("open_time","opentime","data_de_abertura","data_abertura","abertura",
                          "hora_de_abertura","hora_abertura","hora de abertura","open_hour");
  const hasCloseTime = has("close_time","closetime","data_de_fecho","data_fecho","fecho",
                          "hora_de_fecho","hora_fecho","hora de fecho","close_hour");
  const hasVolume    = has("volume","qty","quantity","quantidade");
  const hasProfit    = has("profit","lucro","resultado","pl","profit_loss");
  if (hasSymbolOrSimb && has("type","tipo") && hasOpenTime && hasCloseTime && hasVolume) return "xtb_trades";
  // XTB open positions / portfolio snapshot
  // EN: Symbol,Volume,Open price,Market price  PT: simbolo,volume,preco_de_abertura,preco_atual
  const hasOpenPx  = has("open_price","openprice","preco_de_abertura","preco_abertura","preco_entrada");
  const hasMktPx   = has("market_price","marketprice","preco_atual","preco_mercado","current_price");
  if (hasSymbolOrSimb && hasVolume && hasOpenPx && hasMktPx) return "xtb_positions";
  // XTB cash operations (Tipo, Símbolo/Comentário, Montante, Data)
  // PT: tipo,simbolo,montante,comentario,data  EN: type,symbol,amount,comment,date
  if ((has("tipo","type")) && has("montante","amount","valor") && (hasSymbolOrSimb || has("comentario","comment"))) return "xtb_cash";
  return "unknown";
}

function detectBrokerTextFormat(text) {
  const n = normStr(text || "");
  if (!n) return "unknown";
  // Trading 212 holdings PDF
  if ((n.includes("confirmacao de ativos") || n.includes("confirmation of holdings") || n.includes("trading 212 invest")) && n.includes("valor dos ativos") && n.includes("isin") && n.includes("quantity") && n.includes("price")) {
    return "holdings_pdf";
  }
  // XTB account statement / trade confirmation PDF
  // XTB PDFs typically contain "xtb" in header and have Symbol/Volume/Open/Close columns
  if ((n.includes("xtb") || n.includes("x-trade brokers")) &&
      (n.includes("symbol") || n.includes("simbolo") || n.includes("instrumento")) &&
      (n.includes("volume") || n.includes("profit") || n.includes("lucro"))) {
    return "xtb_pdf";
  }
  return "unknown";
}

function normalizeBrokerNameFromFile(fileName) {
  const n = normStr(fileName || "");
  if (n.includes("divtracker")) return "DivTracker";
  if (n.includes("confirmation-of-holdings") || n.includes("confirmacao") || n.includes("holdings") || n.includes("trading212") || n.includes("trade212")) return "Trading 212";
  if (n.includes("trade republic") || n.includes("from_")) return "Corretora CSV";
  if (n.includes("xtb")) return "XTB";
  return "Corretora";
}

function normalizeBrokerAction(raw) {
  const n = normStr(raw || "");
  if (n.includes("market buy") || n.includes("limit buy")) return "BUY";
  if (n.includes("market sell") || n.includes("limit sell")) return "SELL";
  if (n === "deposit") return "DEPOSIT";
  if (n.includes("withdraw")) return "WITHDRAWAL";
  if (n.includes("interest on cash")) return "CASH_INTEREST";
  if (n.includes("lending interest")) return "LENDING_INTEREST";
  if (n.includes("dividend adjustment")) return "DIVIDEND_ADJ";
  if (n.includes("return of capital")) return "ROC";
  // v63: "Stock dividends" = shares credited, no cash → stock event, not cash dividend
  if (n.includes("stock dividend")) return "STOCK_DISTRIBUTION";
  if (n.includes("adr fee")) return "FEE";
  if (n.startsWith("dividend")) return "DIVIDEND";
  if (n.includes("stock split open")) return "SPLIT_OPEN";
  if (n.includes("stock split close")) return "SPLIT_CLOSE";
  if (n.includes("stock distribution") || n.includes("custom stock distribution")) return "STOCK_DISTRIBUTION";
  if (n.includes("spin off") || n.includes("spin_off")) return "STOCK_DISTRIBUTION"; // treat spin-off as stock event
  return "OTHER";
}

function brokerPositionClassFromTicker(ticker) {
  const upper = String(ticker || "").toUpperCase();
  const plain = upper.replace(/\.CC$/, "");
  const isCrypto = upper.endsWith(".CC") || ["BTC","ETH","SOL","ADA","XRP","DOT","BNB"].includes(plain);
  return isCrypto ? "Cripto" : "Ações/ETFs";
}

function brokerEventKey(evt) {
  // v63b: brokers assign a unique transaction ID per row (XTB "ID" column).
  // XTB pays several identical lots of the same ticker within the SAME second, and
  // the Excel export truncates sub-second precision, so type+time+ticker+amount is
  // NOT unique: 2709 of 4456 dividend rows collided and were silently dropped on
  // import (-1326.85 EUR). When a broker row ID exists, it alone identifies the row.
  const extId = String(evt.extId || "").trim();
  if (extId) return [evt.broker || "", evt.type || "", extId].join("|");
  return [
    evt.type || "", evt.dateTime || evt.date || "", evt.ticker || "", evt.isin || "", evt.name || "",
    Math.round(parseNum(evt.qty) * 1e8) / 1e8,
    Math.round(parseNum(evt.totalEUR) * 100) / 100,
    Math.round(parseNum(evt.grossLocal) * 1e8) / 1e8,
    evt.actionRaw || "", evt.notes || ""
  ].join("|");
}

function brokerPositionKey(pos) {
  return [
    makeBrokerSecurityKey(pos),
    Math.round(parseNum(pos.qty) * 1e8) / 1e8,
    Math.round(parseNum(pos.costBasisEUR) * 100) / 100,
    Math.round(parseNum(pos.marketValueEUR) * 100) / 100,
    pos.positionKind || "",
    pos.snapshotDate || "",
    pos.sourceName || ""
  ].join("|");
}

  window.VestraBrokerParsingCore = Object.freeze({
    normalizeISIN,
    normalizeSecurityNameKey,
    KNOWN_BROKER_YAHOO_OVERRIDES,
    getKnownBrokerYahooOverride,
    canonicalBrokerTickerBase,
    inferPreferredVenueTicker,
    venueFromIsinAndCurrency,
    inferYahooTickerFromIdentity,
    sameSecurityName,
    sameBrokerSecurityIdentity,
    makeBrokerSecurityKey,
    detectBrokerRowsFormat,
    detectBrokerTextFormat,
    normalizeBrokerNameFromFile,
    normalizeBrokerAction,
    brokerPositionClassFromTicker,
    brokerEventKey,
    brokerPositionKey,
  });
})();
