/* Vestra broker workbook/file readers v1.0 — file IO + workbook structure only. */
(() => {
  'use strict';

  const { csvToObjects, normalizeRow } = window.VestraFileParsing || {};
  const { detectBrokerRowsFormat } = window.VestraBrokerParsingCore || {};
  if (![csvToObjects, normalizeRow, detectBrokerRowsFormat].every(fn => typeof fn === 'function')) {
    throw new Error('Broker workbook dependencies were not loaded before app-broker-workbook.js');
  }

async function fileToText(file) {
  return new Promise((res, rej) => {
    const r = new FileReader();
    r.onerror = () => rej(new Error("Erro a ler ficheiro."));
    r.onload = () => res(String(r.result || ""));
    r.readAsText(file);
  });
}

async function fileToObjectRows(file) {
  const name = String(file?.name || "").toLowerCase();
  if (name.endsWith(".xlsx") || name.endsWith(".xls")) {
    if (typeof XLSX === "undefined") throw new Error("Biblioteca Excel não carregada.");
    const ab = await file.arrayBuffer();
    const wb = XLSX.read(ab, { type: "array", raw: false, cellDates: true });
    const sheetName = wb.SheetNames[0];
    if (!sheetName) return [];
    const ws = wb.Sheets[sheetName];
    return XLSX.utils.sheet_to_json(ws, { defval: "", raw: false });
  }
  const text = await fileToText(file);
  return csvToObjects(text);
}

function xtbWorkbookSheetToRows(ws) {
  if (typeof XLSX === "undefined" || !ws) return [];
  const aoa = XLSX.utils.sheet_to_json(ws, { header: 1, defval: "", raw: false });
  if (!Array.isArray(aoa) || !aoa.length) return [];

  const HEADER_HINTS = new Set([
    "id","position","posicao","symbol","simbolo","instrumento","type","tipo","volume","qty","quantity","quantidade",
    "open_time","opentime","close_time","closetime","open_price","close_price","market_price",
    "hora_de_abertura","hora_abertura","hora_de_fecho","hora_fecho",
    "preco_de_abertura","preco_de_fecho","preco_atual","preco_de_mercado",
    "purchase_value","amount","montante","comment","comentario","time","date","data","profit","lucro",
    "commission","comissao","swap","margin","market price","open price","close price"
  ]);

  let bestIdx = -1;
  let bestScore = 0;
  const maxScan = Math.min(aoa.length, 40);

  for (let i = 0; i < maxScan; i++) {
    const row = Array.isArray(aoa[i]) ? aoa[i] : [];
    const normed = row.map(v => normKey(v)).filter(Boolean);
    if (!normed.length) continue;
    let score = 0;
    normed.forEach(k => {
      if (HEADER_HINTS.has(k) || HEADER_HINTS.has(k.replace(/_/g, " "))) score += 2;
    });
    if (normed.includes("symbol") || normed.includes("simbolo") || normed.includes("instrumento")) score += 4;
    if (normed.includes("type") || normed.includes("tipo")) score += 3;
    if (normed.includes("amount") || normed.includes("montante")) score += 3;
    if (normed.includes("open_time") || normed.includes("close_time") ||
        normed.includes("hora_de_abertura") || normed.includes("hora_de_fecho")) score += 3;
    if (normed.includes("market_price") || normed.includes("open_price") ||
        normed.includes("preco_de_abertura") || normed.includes("preco_atual")) score += 3;
    if (score > bestScore) { bestScore = score; bestIdx = i; }
  }
  if (bestIdx < 0 || bestScore < 5) return [];

  const headerRow = Array.isArray(aoa[bestIdx]) ? aoa[bestIdx] : [];
  let startCol = 0;
  while (startCol < headerRow.length && !String(headerRow[startCol] || "").trim()) startCol++;

  const rawHeaders = headerRow.slice(startCol).map(v => String(v || "").trim());
  const headers = rawHeaders.map((h, idx) => h || `__col_${idx}`);
  const out = [];

  for (let r = bestIdx + 1; r < aoa.length; r++) {
    const row = Array.isArray(aoa[r]) ? aoa[r].slice(startCol, startCol + headers.length) : [];
    if (!row.some(v => String(v || "").trim() !== "")) continue;
    const obj = {};
    headers.forEach((h, c) => { obj[h] = row[c] ?? ""; });
    out.push(obj);
  }
  return out;
}

function xtbExtractSheetMeta(ws, sheetName = "") {
  const meta = { asOfDate: "", sheetName: String(sheetName || "") };
  try {
    if (typeof XLSX === "undefined" || !ws) return meta;
    const aoa = XLSX.utils.sheet_to_json(ws, { header: 1, defval: "", raw: false });
    const nameMatch = String(sheetName || "").match(/(\d{2})(\d{2})(\d{4})/);
    if (nameMatch) meta.asOfDate = `${nameMatch[3]}-${nameMatch[2]}-${nameMatch[1]}`;
    if (!meta.asOfDate) {
      for (let i = 0; i < Math.min(15, aoa.length); i++) {
        const row = Array.isArray(aoa[i]) ? aoa[i] : [];
        for (const cell of row) {
          const s = String(cell || "").trim();
          const m = s.match(/(\d{2})\/(\d{2})\/(\d{4})/);
          if (m) { meta.asOfDate = `${m[3]}-${m[2]}-${m[1]}`; break; }
        }
        if (meta.asOfDate) break;
      }
    }
  } catch(_) {}
  return meta;
}

function workbookToBrokerBlocks(wb) {
  const blocks = [];
  if (typeof XLSX === "undefined" || !wb || !Array.isArray(wb.SheetNames)) return blocks;
  for (const sheetName of wb.SheetNames) {
    const ws = wb.Sheets[sheetName];
    const rows = xtbWorkbookSheetToRows(ws);
    if (!rows.length) continue;
    const format = detectBrokerRowsFormat(rows);
    if (format === "unknown") continue;
    blocks.push({ sheetName, format, rows, meta: xtbExtractSheetMeta(ws, sheetName) });
  }
  return blocks;
}

  window.VestraBrokerWorkbook = Object.freeze({
    fileToText,
    fileToObjectRows,
    xtbWorkbookSheetToRows,
    xtbExtractSheetMeta,
    workbookToBrokerBlocks,
  });
})();
