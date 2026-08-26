/* Vestra generic file parsing v1.0 — CSV/row normalization only. */
(() => {
  'use strict';

function splitCSVLine(line, delim) {
  const out = []; let cur = "", q = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') { if (q && line[i + 1] === '"') { cur += '"'; i++; continue; } q = !q; continue; }
    if (!q && ch === delim) { out.push(cur); cur = ""; continue; }
    cur += ch;
  }
  out.push(cur);
  return out;
}

function csvToObjects(text) {
  const raw = String(text || "").replace(/^\uFEFF/, "");
  const lines = raw.split(/\r?\n/);
  const headerHints = ["tipo","type","class","classe","nome","name","ticker","symbol","valor","value","market","yield","amount","data","date","categoria","category","shares","qty"];

  function scoreHeader(line, delim) {
    const cols = splitCSVLine(line, delim).map(c => String(c || "").trim().toLowerCase());
    if (cols.length < 2) return -1;
    let hits = 0;
    for (const c of cols) for (const h of headerHints) if (c === h || c.includes(h)) { hits++; break; }
    return hits;
  }

  let bestDelim = ",", bestScore = -1;
  for (const d of [",", ";", "\t", "|"]) {
    for (let i = 0; i < Math.min(5, lines.length); i++) {
      if (!lines[i] || !lines[i].trim()) continue;
      const s = scoreHeader(lines[i], d);
      if (s > bestScore) { bestScore = s; bestDelim = d; }
    }
  }

  let headerIdx = -1;
  for (let i = 0; i < lines.length; i++) {
    if (!lines[i] || !lines[i].trim()) continue;
    if (scoreHeader(lines[i], bestDelim) >= 1) { headerIdx = i; break; }
  }
  if (headerIdx < 0) headerIdx = 0;

  const header = splitCSVLine(lines[headerIdx], bestDelim).map(h => String(h || "").trim());
  const out = [];
  for (let i = headerIdx + 1; i < lines.length; i++) {
    const line = lines[i];
    if (!line || !line.trim()) continue;
    const cols = splitCSVLine(line, bestDelim);
    const obj = {};
    for (let j = 0; j < header.length; j++) obj[header[j]] = (cols[j] !== undefined) ? cols[j] : "";
    const any = Object.values(obj).some(v => String(v || "").trim() !== "");
    if (any) out.push(obj);
  }
  return out;
}

function normKey(k) {
  return String(k || "").trim().toLowerCase()
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "") // strip accents: símbolo→simbolo
    .replace(/[\u00A0]/g, " ").replace(/[^\p{L}\p{N}]+/gu, "_").replace(/^_+|_+$/g, "");
}

function normalizeRow(obj) {
  const out = {};
  for (const k in (obj || {})) out[normKey(k)] = String(obj[k] ?? "").trim();
  return out;
}

function parseNumberSmart(x) {
  if (x === null || x === undefined) return NaN;
  let s = String(x).trim().replace(/[%€$£]/g, "").replace(/\s/g, "");
  let neg = false;
  if (s.startsWith("(") && s.endsWith(")")) { neg = true; s = s.slice(1, -1); }
  const hasComma = s.includes(","), hasDot = s.includes(".");
  if (hasComma && hasDot) {
    if (s.lastIndexOf(",") > s.lastIndexOf(".")) s = s.replace(/\./g, "").replace(",", ".");
    else s = s.replace(/,/g, "");
  } else if (hasComma && !hasDot) s = s.replace(",", ".");
  else s = s.replace(/,/g, "");
  const n = Number(s);
  return Number.isFinite(n) ? (neg ? -n : n) : NaN;
}

function classifyRow(r) {
  const tipo = (r.tipo || r.type || "").toLowerCase();
  if (["ativo","asset","assets"].includes(tipo)) return "ativo";
  if (["passivo","liability","debt","liabilities"].includes(tipo)) return "passivo";
  if (["movimento","transaction","movement","cashflow","tx","dividend"].includes(tipo)) return "movimento";
  const hasDate = !!(r.data || r.date || r.payment_date || r.trade_date);
  const amount = parseNumberSmart(r.montante || r.amount || r.valor || r.value || r.cash || r.total || r.net);
  const qty = parseNumberSmart(r.qty || r.quantity || r.shares || r.units);
  const mv = parseNumberSmart(r.market_value || r.current_value || r.total_value || r.value || r.valor);
  const hasTicker = !!(r.ticker || r.symbol);
  const cps = parseNumberSmart(r.cost_per_share || r.price || r.preco);
  if (hasTicker && Number.isFinite(qty) && Number.isFinite(cps)) return "trade";
  if (hasDate && Number.isFinite(amount) && Math.abs(amount) > 0) return "movimento";
  const hasId = !!(r.ticker || r.symbol || r.isin || r.nome || r.name);
  if (hasId && Number.isFinite(mv) && mv > 0) return "ativo";
  if (hasId && Number.isFinite(amount) && !hasDate && amount > 0) return "ativo";
  if (Number.isFinite(mv) && mv > 0) return "ativo";
  return "unknown";
}

  window.VestraFileParsing = Object.freeze({
    splitCSVLine,
    csvToObjects,
    normKey,
    normalizeRow,
    parseNumberSmart,
    classifyRow,
  });
})();
