/* Vestra XTB normalization v1.0. */
(() => {
  "use strict";
  const { normStr } = window.VestraUtils || {};
  if (typeof normStr !== "function") throw new Error("VestraUtils.normStr unavailable");

function parseXTBNormalizeAction(type, comment) {
  const t = normStr(type || "");
  const c = normStr(comment || "");
  // Closed trade types
  if (t === "buy" || t === "compra" || t === "bought" || t === "compra_mercado" || t === "compra_limite") return "BUY";
  if (t === "sell" || t === "venda" || t === "sold" || t === "venda_mercado" || t === "venda_limite") return "SELL";
  // Cash operations
  if (t.includes("deposit") || t.includes("deposito") || t.includes("depositar") || c.includes("deposit")) return "DEPOSIT";
  if (t.includes("withdraw") || t.includes("levantamento") || t.includes("retirada") || t.includes("levantar")) return "WITHDRAWAL";
  // v63b: the TYPE column is authoritative — test withholding BEFORE dividend.
  // Two real rows are typed "Withholding tax" but carry the comment
  // "US Dividends Reclassification", so the comment-based dividend test fired
  // first and booked withheld tax as income (+8.30 EUR of phantom dividends).
  if (t.includes("withholding") || t.includes("wht") || t.includes("imposto retido") ||
      t.includes("retencao na fonte") || t.includes("retencao")) return "DIVIDEND_TAX";
  // XTB often exports the typo "DIVIDENT"; also PT "Dividendo"
  if (t.includes("divident") || t.includes("dividend") || t.includes("dividendo")) return "DIVIDEND";
  // Fall back to the comment only when the type itself is uninformative
  if (c.includes(" wht ") || c.includes("retido na fonte")) return "DIVIDEND_TAX";
  if (c.includes("dividend") || c.includes("dividendo")) return "DIVIDEND";
  // Swap = overnight/financing cost → treat as cost (WITHDRAWAL)
  if (t === "swap" || t.includes("rollover") || t.includes("overnight") || t.includes("financiamento")) return "WITHDRAWAL";
  // Interest on cash balance — PT: "Juros sobre saldo", "Juro sobre saldo"
  if ((t.includes("juro") || t.includes("interest")) &&
      !t.includes("swap") && !t.includes("tax") && !t.includes("imposto") && !t.includes("retencao")) return "CASH_INTEREST";
  if (c.includes("interest on") && !c.includes("swap")) return "CASH_INTEREST";
  // Interest tax
  if ((t.includes("interest") && t.includes("tax")) || c.includes("interest tax")) return "CASH_INTEREST_TAX";
  // Commission as separate cash op
  if (t.includes("commission") || t.includes("comissao") || t === "taxa") return "OTHER";
  // "Stock purchase" / "Stock sale" in XTB cash ledger
  // New XTB export format has no OPEN POSITION sheet — Cash Operations IS the position source
  // Map to BUY/SELL so rebuildBrokerGeneratedData can reconstruct open positions
  if (t.includes("stock purchase")) return "XTB_STOCK_PURCHASE";
  if (t.includes("stock sale") || t.includes("stock sell")) return "XTB_STOCK_SALE";
  // "close trade" = closed CFD/position record → skip (P&L from CLOSED sheet)
  if (t.includes("close trade") || t.includes("fechar") || t.includes("closing")) return "OTHER";
  // "fractional shares" = fractional DRS credit → skip
  if (t.includes("fractional")) return "OTHER";
  // Spin-off = corporate action → skip (no cash in/out)
  if (t.includes("spin") || t.includes("spin_off")) return "OTHER";
  // Transaction taxes / fees → skip
  if (t.includes("stamp") || t.includes("sec fee") || t.includes("iftt") || t.includes("tobin")) return "OTHER";
  // XTB EN: "Free-funds Interest" → CASH_INTEREST (already handled by interest check above, this is a fallback)
  // XTB PT: "Correcao de saldo" or "Ajuste de saldo"
  if (t.includes("correc") || t.includes("ajuste") || t.includes("adjustment") || t.includes("correction")) return "OTHER";
  // Legacy: some XTB exports mark stock ops as "stock" type → skip
  if (t.includes("stock") || t.includes("acao") || t.includes("etf")) return "OTHER";
  return "OTHER";
}

function xtbTickerToYahoo(symbol) {
  // XTB uses suffixes like AAPL.US, VOW3.DE, VWCE.DE, etc.
  if (!symbol) return symbol;
  const s = symbol.toUpperCase().trim();
  const directMap = {
    // Brookfield Asset Management — XTB exports "BAM1.US", Yahoo uses "BAM" (NYSE)
    "BAM1.US":"BAM",
    "BAM1":"BAM",
    // Volkswagen preference shares — XTB "VOW1.DE", Yahoo Xetra is VOW3.DE (VOW.DE is delisted)
    "VOW1.DE":"VOW3.DE",
    "VOW1":"VOW3.DE",
    // VanEck Junior Gold Miners UCITS — Xetra symbol G2XJ
    "GDXJ.DE":"G2XJ.DE",
    // Novo Nordisk B — Copenhagen uses hyphen in Yahoo
    "NOVOB.DK":"NOVO-B.CO",
    "NOVOB":"NOVO-B.CO",
    // STMicroelectronics Paris listing
    "STM.FR":"STMPA.PA",
    // Medical Properties Trust NYSE
    "MPW.US":"MPW",
    "MPW":"MPW",
    // Novonesis / legacy Novozymes B code used by XTB
    "NZYMB.DK":"NSIS-B.CO",
    // AMS-OSRAM Vienna listing
    "AMS":"AMS2.VI",
    // iShares NASDAQ US Biotech UCITS — listed in London, not Xetra
    "BTEC.DE":"BTEC.L",
    // Explicit XTB→Yahoo mappings for assets with different names across brokers
    "ADM.US":"ADM",    // Archer-Daniels-Midland (XTB name="ADM", T212 name="Archer-Daniels-Midland")
    "BMY.US":"BMY",    // Bristol-Myers Squibb (XTB name="BMS")
    "NESN.CH":"NESN.SW" // Nestlé (XTB .CH → Yahoo .SW)
  };
  if (directMap[s]) return directMap[s];
  // Remove .US suffix – Yahoo uses bare ticker for US stocks
  if (s.endsWith(".US")) return s.slice(0, -3);
  // .PT → .LS (Euronext Lisbon)
  if (s.endsWith(".PT")) return s.slice(0, -3) + ".LS";
  // .UK → .L (London)
  if (s.endsWith(".UK")) return s.slice(0, -3) + ".L";
  // .HK → .HK (Hong Kong — same)
  // .CN → .SS or .SZ (China — can't determine, keep as-is)
  // .SG → .SI (Singapore)
  if (s.endsWith(".SG")) return s.slice(0, -3) + ".SI";
  // .AU → .AX (Australia)
  if (s.endsWith(".AU")) return s.slice(0, -3) + ".AX";
  // .JP → .T (Tokyo)
  if (s.endsWith(".JP")) return s.slice(0, -3) + ".T";
  // European exchange suffixes
  if (s.endsWith(".CH")) return s.slice(0, -3) + ".SW";  // Swiss → SIX (e.g. NESN.CH → NESN.SW)
  if (s.endsWith(".PL")) return s.slice(0, -3) + ".WA";  // Poland → Warsaw
  if (s.endsWith(".DK")) return s.slice(0, -3) + ".CO";  // Denmark → Copenhagen
  if (s.endsWith(".SE")) return s.slice(0, -3) + ".ST";  // Sweden → Stockholm
  if (s.endsWith(".NO")) return s.slice(0, -3) + ".OL";  // Norway → Oslo
  if (s.endsWith(".FI")) return s.slice(0, -3) + ".HE";  // Finland → Helsinki
  if (s.endsWith(".BE")) return s.slice(0, -3) + ".BR";  // Belgium → Brussels
  if (s.endsWith(".IT")) return s.slice(0, -3) + ".MI";  // Italy → Milan
  if (s.endsWith(".FR")) return s.slice(0, -3) + ".PA";  // France → Paris
  if (s.endsWith(".NL")) return s.slice(0, -3) + ".AS";  // Netherlands → Amsterdam
  if (s.endsWith(".ES")) return s.slice(0, -3) + ".MC";  // Spain → Madrid
  return s;
}

function xtbSymbolCurrency(symbol) {
  const s = String(symbol || "").toUpperCase().trim();
  const suff = s.includes('.') ? s.split('.').pop() : '';
  const map = {
    US: 'USD', UK: 'GBP', PT: 'EUR', DE: 'EUR', FR: 'EUR', ES: 'EUR', NL: 'EUR', IT: 'EUR', BE: 'EUR', AT: 'EUR', IE: 'EUR',
    CH: 'CHF', PL: 'PLN', DK: 'DKK', SE: 'SEK', NO: 'NOK', TO: 'CAD', V: 'CAD', NE: 'CAD',
    AU: 'AUD', AX: 'AUD', BR: 'EUR', LS: 'EUR', L: 'GBP', SW: 'CHF', MC: 'EUR', VI: 'EUR', PA: 'EUR', F: 'EUR', T: 'JPY'
  };
  return map[suff] || 'EUR';
}


  window.VestraXtbNormalization = Object.freeze({
    parseXTBNormalizeAction, xtbTickerToYahoo, xtbSymbolCurrency
  });
})();
