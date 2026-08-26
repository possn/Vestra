from pathlib import Path

app = Path('app.js')
utils = Path('app-utils.js')

src = app.read_text(encoding='utf-8')
ut = utils.read_text(encoding='utf-8')

block = '''function normalizeClassName(s) {
  const map = {
    "stock":"Ações/ETFs","etf":"Ações/ETFs","equity":"Ações/ETFs","fund":"Fundos",
    "crypto":"Cripto","gold":"Ouro","silver":"Prata","real estate":"Imobiliário",
    "deposit":"Depósitos","cash":"Liquidez","ppr":"PPR","debt":"Dívida"
  };
  const n = normStr(s || "");
  for (const [k,v] of Object.entries(map)) { if (n.includes(k)) return v; }
  return s || "Outros";
}

function normalizeYieldType(s) {
  const n = normStr(s || "");
  if (n.includes("pct") || n.includes("%") || n.includes("percent")) return "yield_pct";
  if (n.includes("eur") || n.includes("year") || n.includes("annual")) return "yield_eur_year";
  if (n.includes("rent") || n.includes("month")) return "rent_month";
  return "none";
}

'''

if src.count(block) != 1:
    raise SystemExit('Normalization block not found exactly once in app.js')

anchor = "  window.VestraUtils = Object.freeze({normStr,escapeHtml,uid,isoToday,safeClone,parseNum,parseQty,normalizeDate,formatNumber});"
if ut.count(anchor) != 1:
    raise SystemExit('VestraUtils export anchor not unique')

insert = '''  function normalizeClassName(s) {
    const map = {
      "stock":"Ações/ETFs","etf":"Ações/ETFs","equity":"Ações/ETFs","fund":"Fundos",
      "crypto":"Cripto","gold":"Ouro","silver":"Prata","real estate":"Imobiliário",
      "deposit":"Depósitos","cash":"Liquidez","ppr":"PPR","debt":"Dívida"
    };
    const n = normStr(s || "");
    for (const [k,v] of Object.entries(map)) { if (n.includes(k)) return v; }
    return s || "Outros";
  }

  function normalizeYieldType(s) {
    const n = normStr(s || "");
    if (n.includes("pct") || n.includes("%") || n.includes("percent")) return "yield_pct";
    if (n.includes("eur") || n.includes("year") || n.includes("annual")) return "yield_eur_year";
    if (n.includes("rent") || n.includes("month")) return "rent_month";
    return "none";
  }

'''

if 'function normalizeClassName(s)' not in ut:
    ut = ut.replace(anchor, insert + '  window.VestraUtils = Object.freeze({normStr,escapeHtml,uid,isoToday,safeClone,parseNum,parseQty,normalizeDate,formatNumber,normalizeClassName,normalizeYieldType});', 1)
elif 'normalizeClassName,normalizeYieldType' not in ut:
    raise SystemExit('Unexpected partially migrated app-utils.js')

src = src.replace(block, '', 1)
src = src.replace('  formatNumber,\n} = window.VestraUtils || {};', '  formatNumber,\n  normalizeClassName,\n  normalizeYieldType,\n} = window.VestraUtils || {};', 1)
src = src.replace('if (![normStr, escapeHtml, uid, isoToday, safeClone, parseNum, parseQty, normalizeDate, formatNumber].every(fn => typeof fn === "function")) {', 'if (![normStr, escapeHtml, uid, isoToday, safeClone, parseNum, parseQty, normalizeDate, formatNumber, normalizeClassName, normalizeYieldType].every(fn => typeof fn === "function")) {', 1)

if 'function normalizeClassName(s)' in src or 'function normalizeYieldType(s)' in src:
    raise SystemExit('Normalization helpers still present in app.js')
if 'normalizeClassName,normalizeYieldType' not in ut:
    raise SystemExit('Normalization helpers not exported by app-utils.js')

app.write_text(src, encoding='utf-8')
utils.write_text(ut, encoding='utf-8')
print('Moved class/yield normalization helpers to app-utils.js')
