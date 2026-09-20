/* Vestra broker workbook/file readers v1.3 — file IO, workbook structure + bank categorisation. */
(() => {
  'use strict';

  const { csvToObjects, normKey, normalizeRow } = window.VestraFileParsing || {};
  const { detectBrokerRowsFormat } = window.VestraBrokerParsingCore || {};
  if (![csvToObjects, normKey, normalizeRow, detectBrokerRowsFormat].every(fn => typeof fn === 'function')) {
    throw new Error('Broker workbook dependencies were not loaded before app-broker-workbook.js');
  }

  async function ensureXlsx() {
    if (window.XLSX) return window.XLSX;
    const loader = window.VestraXlsxLoader;
    if (!loader?.ensure) throw new Error("Carregador Excel não disponível.");
    return loader.ensure();
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
    await ensureXlsx();
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

function categoriseBankTransaction(desc, dir) {
  const d = String(desc || '')
    .toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, ' ').trim();

  if (dir === "in") {
    if (/salario|vencimento|remuneracao|ordenado/.test(d)) return "Salário";
    if (/subsidio|sub\. ?ferias|sub\. ?natal/.test(d)) return "Subsídio";
    if (/renda|aluguer|arrendamento/.test(d)) return "Renda recebida";
    if (/dividendo|dividend/.test(d)) return "Dividendos";
    if (/reembolso|devolucao|devol\./.test(d)) return "Reembolso";
    if (/transferencia de|trf\. de|trf\.imed\. de|recebido de/.test(d)) return "Transferência recebida";
    if (/mb way/.test(d)) return "MB Way recebido";
    if (/transferencia entre contas/.test(d)) return "Transferência entre contas";
    if (/^poupan|pouoanca|poupanca noutra/.test(d)) return "Poupança própria";
    if (/mesada pedro|mesada miudos/.test(d)) return "Mesada";
    if (/constituicao de d\.p|constituicao de dp/.test(d)) return "Constituição DP";
    if (/irs|at |autoridade tributaria/.test(d)) return "Reembolso IRS";
    if (/seguranca social|seg\. social/.test(d)) return "Segurança Social";
    if (/pensao|reforma/.test(d)) return "Pensão";
  }

  if (/hipoteca|credito habitacao|credito \/ habitacao|ch /.test(d)) return "Crédito habitação";
  if (/condominio|cond\./.test(d)) return "Condomínio";
  if (/renda|aluguer/.test(d) && dir === "out") return "Renda";
  if (/agua|aguas de|aguas do/.test(d)) return "Água";
  if (/luz|eletricidade|edp|ibelectra|e\.on/.test(d)) return "Electricidade";
  if (/gas |galp|gas natural/.test(d)) return "Gás";
  if (/internet|meo|nos |vodafone|nowo|altice/.test(d)) return "Telecomunicações";
  if (/seguro de vida/.test(d)) return "Seguro de vida";
  if (/seguro multi.riscos|seguro multiriscos/.test(d)) return "Seguro multirriscos";
  if (/seguro |ageas|fidelidade|tranquilidade|zurich|allianz|chubb/.test(d)) return "Seguros";
  if (/via verde|autoestrada/.test(d)) return "Via Verde";
  if (/combustivel|galp|bp |repsol|shell/.test(d)) return "Combustível";
  if (/comboio|cp |metro |autocarro|uber|bolt/.test(d)) return "Transportes";
  if (/estacionamento|parque/.test(d)) return "Estacionamento";
  if (/levantamento|atm|multibanco/.test(d)) return "Levantamento";
  if (/continente|pingo doce|lidl|aldi|minipreco|minipreço|mercadona|supermercado/.test(d)) return "Supermercado";
  if (/restaurante|cafe |snack|pizza|mcdonalds|kfc|nandos|sushi/.test(d)) return "Restaurante";
  if (/padaria|pastelaria|confeitaria/.test(d)) return "Padaria";
  if (/farmacia|farmácia|medicina|clinica|hospital|dentista|consultorio/.test(d)) return "Saúde";
  if (/ginasio|gym|fitness|coolgym|holmes|virgin/.test(d)) return "Ginásio";
  if (/imposto|irs |iva |iuc |imt |at |fisco|tributaria/.test(d)) return "Impostos";
  if (/comissao|comissão|manutencao conta/.test(d)) return "Comissões bancárias";
  if (/deposito a prazo|constituicao de d\.p|dp |d\.p\./.test(d)) return "Constituição DP";
  if (/ppr |plano poupanca|subscricao ppr/.test(d)) return "PPR";
  if (/investimento|subscricao|fundo/.test(d)) return "Investimento";
  if (/^poupan|pouoanca|poupanca noutra/.test(d)) return "Poupança própria";
  if (/mesada pedro|mesada miudos/.test(d)) return "Mesada";
  if (/transferencia entre contas/.test(d)) return "Transferência entre contas";
  if (/cred\.|credito consumo|credito pessoal/.test(d)) return "Crédito pessoal";
  if (/cartao|pagamento de conta cartao/.test(d)) return "Cartão de crédito";
  if (/escola|colegio|universidade|propina|aulas|explicador/.test(d)) return "Educação";
  if (/netflix|spotify|amazon|apple\.com|google|disney|hbo/.test(d)) return "Subscrições";
  if (/cinema|teatro|concerto|bilhete/.test(d)) return "Lazer";
  if (/mb way para|mb way emitida|trf\. mb way para/.test(d)) return "MB Way enviado";
  if (/transferencia para|trf\. para|transferencia emitida|trf\. emitida/.test(d)) return "Transferência enviada";
  if (/servicos municip|camara|municipal|municipio/.test(d)) return "Serviços municipais";
  if (/trf\.imed\. p\/|trf\.imed\.para|transferencia para revolut|para revolut/.test(d)) return "Transferência poupança";
  if (/mb way/.test(d) && dir === "out") return "MB Way enviado";
  if (/quota mensal|quota|varzea de sintra|recreativa|associacao|sociedade recreativa/.test(d)) return "Quotas associações";
  return dir === "in" ? "Outros recebimentos" : "Outras despesas";
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
    const dateFromCell = cell => {
      const s = String(cell || "").trim();
      const iso = s.match(/(\d{4})-(\d{2})-(\d{2})/);
      const dmy = s.match(/(\d{2})\/(\d{2})\/(\d{4})/);
      if (iso) return `${iso[1]}-${iso[2]}-${iso[3]}`;
      if (dmy) return `${dmy[3]}-${dmy[2]}-${dmy[1]}`;
      return "";
    };
    if (!meta.asOfDate) {
      const scanned = aoa.slice(0, 15).map(row => Array.isArray(row) ? row : []);
      // XTB includes both a historical "Date from" and the actual report cutoff.
      // Prefer the explicit report/as-of or Date to control so an old start date
      // never labels a current position snapshot.
      const priority = scanned.filter(row => /data as of report generated|date to \(utc\)|data do relatorio|data ate/i.test(String(row[0] || "")));
      for (const row of [...priority, ...scanned]) {
        for (const cell of row) {
          const parsed = dateFromCell(cell);
          if (parsed) { meta.asOfDate = parsed; break; }
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
    categoriseBankTransaction,
    xtbWorkbookSheetToRows,
    xtbExtractSheetMeta,
    workbookToBrokerBlocks,
  });
})();
