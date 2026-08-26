from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.js"
INDEX = ROOT / "index.html"

START = "/* ─── UTILS ───────────────────────────────────────────────── */"
END = "/* ─── INFO TIPS (explicações contextuais) ─────────────────── */"

NEW_UTILS = r'''/* ─── UTILS — shared pure helpers live in app-utils.js ───────── */
const {
  normStr,
  escapeHtml,
  uid,
  isoToday,
  safeClone,
  parseNum,
  parseQty,
  normalizeDate,
  formatNumber,
} = window.VestraUtils || {};

if (![normStr, escapeHtml, uid, isoToday, safeClone, parseNum, parseQty, normalizeDate, formatNumber].every(fn => typeof fn === "function")) {
  throw new Error("VestraUtils não foi carregado antes de app.js");
}

function fmtEUR(n) {
  const cur = (state.settings && state.settings.currency) || "EUR";
  const v = Number(n || 0);
  try {
    return new Intl.NumberFormat("pt-PT", { style: "currency", currency: cur, maximumFractionDigits: 0 }).format(v);
  } catch { return Math.round(v) + " " + cur; }
}

function fmtEUR2(n) {
  const cur = (state.settings && state.settings.currency) || "EUR";
  const v = Number(n || 0);
  try {
    return new Intl.NumberFormat("pt-PT", { style: "currency", currency: cur, maximumFractionDigits: 2 }).format(v);
  } catch { return v.toFixed(2) + " " + cur; }
}

function fmt(n, maxFrac = 4) { return formatNumber(n, maxFrac); }
function fmtPct(n) { return fmt(n, 2) + "%"; }

function normalizeClassName(s) {
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


def patch_app():
    text = APP.read_text(encoding="utf-8")
    if "VestraUtils não foi carregado antes de app.js" in text:
        print("app.js already migrated")
        return False
    if text.count(START) != 1 or text.count(END) != 1:
        raise RuntimeError("Unexpected app.js utility markers")
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    updated = before + NEW_UTILS + END + after
    # Guard the migration: old definitions must be gone from the app monolith.
    for legacy in ["function parseNum(x)", "function parseQty(x)", "function normalizeDate(s)", "function safeClone(obj)"]:
        if legacy in updated[: updated.index(END)]:
            raise RuntimeError(f"Legacy helper still present before INFO TIPS: {legacy}")
    APP.write_text(updated, encoding="utf-8")
    return True


def patch_index():
    text = INDEX.read_text(encoding="utf-8")
    app_tag = '<script defer="" fetchpriority="high" src="app.js?v=20260824v11"></script>'
    util_tag = '<script defer="" src="app-utils.js?v=1.0"></script>'
    if util_tag not in text:
        if text.count(app_tag) != 1:
            raise RuntimeError("Could not locate canonical app.js script tag")
        text = text.replace(app_tag, util_tag + "\n" + app_tag, 1)
        INDEX.write_text(text, encoding="utf-8")
        return True
    if text.index(util_tag) > text.index(app_tag):
        raise RuntimeError("app-utils.js must load before app.js")
    print("index.html already loads app-utils.js first")
    return False


changed = patch_app() | patch_index()
if not changed:
    print("No changes required")
else:
    print("Stage-one app modularization applied")
