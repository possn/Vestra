from pathlib import Path


def once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match, got {count}")
    return text.replace(old, new, 1)


path = Path("worker.js")
s = path.read_text(encoding="utf-8")

s = once(
    s,
    " * Versão 4.4 — fresh quote overlay + cached market fundamentals",
    " * Versão 4.5 — null-safe fundamentals + fresh quote overlay",
    "worker version header",
)

s = once(
    s,
    """function raw(node) {
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
""",
    """function raw(node) {
  if (node == null) return null;
  if (typeof node === 'number' || typeof node === 'string') return node;
  return node.raw ?? node.fmt ?? null;
}

function numberOrNull(node) {
  const value = raw(node);
  if (value === null || value === undefined || value === '') return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function pctRaw(node) {
  const v = numberOrNull(node);
  if (v === null) return null;
  return Math.abs(v) <= 1 ? v * 100 : v;
}

function isoFromUnix(v) {
  const n = numberOrNull(v);
  if (n === null || n <= 0) return '';
""",
    "null-safe numeric helper",
)

s = once(
    s,
    """    const v = Number(raw(sorted[i]?.reportedValue));
    if (Number.isFinite(v)) return v;
""",
    """    const v = numberOrNull(sorted[i]?.reportedValue);
    if (v !== null) return v;
""",
    "latest timeseries null safety",
)

s = once(
    s,
    """    .map(x => Number(raw(x?.reportedValue))).filter(Number.isFinite);
""",
    """    .map(x => numberOrNull(x?.reportedValue)).filter(v => v !== null);
""",
    "previous timeseries null safety",
)

s = once(s, "const cacheUrl = `https://cache.internal/market41:${canonical}`;", "const cacheUrl = `https://cache.internal/market45:${canonical}`;", "market cache generation")

s = once(
    s,
    """      const current = Number(quote?.price);
      if (Number.isFinite(current) && current > 0) {
""",
    """      const current = numberOrNull(quote?.price);
      if (current !== null && current > 0) {
""",
    "cache-hit current price",
)

s = once(
    s,
    """          const value = Number(quote?.[quoteKey]);
          if (Number.isFinite(value)) data[targetKey] = value;
""",
    """          const value = numberOrNull(quote?.[quoteKey]);
          if (value !== null) data[targetKey] = value;
""",
    "cache-hit quote metric overlay",
)

s = once(
    s,
    """        const target = Number(data.analyst_price_target_mean);
        if (Number.isFinite(target)) data.analyst_price_target_upside_pct = ((target / current) - 1) * 100;
        const fcf = Number(data.free_cash_flow);
        const marketCap = Number(data.market_cap);
        if (Number.isFinite(fcf) && Number.isFinite(marketCap) && marketCap > 0) data.fcf_yield = (fcf / marketCap) * 100;
""",
    """        const target = numberOrNull(data.analyst_price_target_mean);
        data.analyst_price_target_upside_pct = target !== null && target > 0 ? ((target / current) - 1) * 100 : null;
        const fcf = numberOrNull(data.free_cash_flow);
        const marketCap = numberOrNull(data.market_cap);
        data.fcf_yield = fcf !== null && marketCap !== null && marketCap > 0 ? (fcf / marketCap) * 100 : null;
""",
    "cache-hit derived metrics",
)

s = once(
    s,
    """    history = ts.map((t,i)=>({date:new Date(t*1000).toISOString().slice(0,10),close:Number(closes[i])})).filter(x=>Number.isFinite(x.close));
""",
    """    history = ts.map((t,i)=>{
      const close = numberOrNull(closes[i]);
      return close !== null && close > 0 ? {date:new Date(t*1000).toISOString().slice(0,10),close} : null;
    }).filter(Boolean);
""",
    "chart null closes",
)

s = once(
    s,
    """  const marketCap = Number(raw(price.marketCap) ?? raw(sd.marketCap));
  const fcf = Number(raw(fd.freeCashflow));
  const target = Number(raw(fd.targetMeanPrice));
  const current = Number(quote.price);
""",
    """  const marketCap = firstFinite(numberOrNull(price.marketCap), numberOrNull(sd.marketCap), numberOrNull(quote.market_cap));
  const fcf = numberOrNull(fd.freeCashflow);
  const target = numberOrNull(fd.targetMeanPrice);
  const current = numberOrNull(quote.price);
""",
    "market primary numeric inputs",
)

replacements = [
    ("current_price: Number.isFinite(current) ? current : null,", "current_price: current,"),
    ("market_cap: firstFinite(Number.isFinite(marketCap) ? marketCap : null, Number(quote.market_cap)),", "market_cap: marketCap,"),
    ("trailing_pe: firstFinite(Number(raw(sd.trailingPE)), Number(raw(ks.trailingPE)), Number(quote.trailing_pe)),", "trailing_pe: firstFinite(numberOrNull(sd.trailingPE), numberOrNull(ks.trailingPE), numberOrNull(quote.trailing_pe)),"),
    ("forward_pe: firstFinite(Number(raw(sd.forwardPE)), Number(raw(ks.forwardPE)), Number(quote.forward_pe)),", "forward_pe: firstFinite(numberOrNull(sd.forwardPE), numberOrNull(ks.forwardPE), numberOrNull(quote.forward_pe)),"),
    ("price_to_book: firstFinite(Number(raw(ks.priceToBook)), Number(quote.price_to_book)),", "price_to_book: firstFinite(numberOrNull(ks.priceToBook), numberOrNull(quote.price_to_book)),"),
    ("enterprise_to_ebitda: Number(raw(ks.enterpriseToEbitda)),", "enterprise_to_ebitda: numberOrNull(ks.enterpriseToEbitda),"),
    ("operating_cash_flow: firstFinite(Number(raw(fd.operatingCashflow)), ocfAnnual),", "operating_cash_flow: firstFinite(numberOrNull(fd.operatingCashflow), ocfAnnual),"),
    ("free_cash_flow: firstFinite(Number.isFinite(fcf) ? fcf : null, fcfAnnual),", "free_cash_flow: firstFinite(fcf, fcfAnnual),"),
    ("fcf_yield: Number.isFinite(firstFinite(Number.isFinite(fcf) ? fcf : null, fcfAnnual)) && Number.isFinite(marketCap) && marketCap > 0 ? (firstFinite(Number.isFinite(fcf) ? fcf : null, fcfAnnual) / marketCap) * 100 : null,", "fcf_yield: firstFinite(fcf, fcfAnnual) !== null && marketCap !== null && marketCap > 0 ? (firstFinite(fcf, fcfAnnual) / marketCap) * 100 : null,"),
    ("debt_to_equity: firstFinite(Number(raw(fd.debtToEquity)), Number.isFinite(debtAnnual) && Number.isFinite(equityAnnual) && equityAnnual !== 0 ? debtAnnual/equityAnnual*100 : null),", "debt_to_equity: firstFinite(numberOrNull(fd.debtToEquity), Number.isFinite(debtAnnual) && Number.isFinite(equityAnnual) && equityAnnual !== 0 ? debtAnnual/equityAnnual*100 : null),"),
    ("current_ratio: Number(raw(fd.currentRatio)),", "current_ratio: numberOrNull(fd.currentRatio),"),
    ("quick_ratio: Number(raw(fd.quickRatio)),", "quick_ratio: numberOrNull(fd.quickRatio),"),
    ("analyst_price_target_mean: Number.isFinite(target) ? target : null,", "analyst_price_target_mean: target !== null && target > 0 ? target : null,"),
    ("analyst_price_target_upside_pct: Number.isFinite(target) && Number.isFinite(current) && current > 0 ? ((target/current)-1)*100 : null,", "analyst_price_target_upside_pct: target !== null && target > 0 && current !== null && current > 0 ? ((target/current)-1)*100 : null,"),
    ("fifty_two_week_high: Number(raw(sd.fiftyTwoWeekHigh)),", "fifty_two_week_high: firstFinite(numberOrNull(sd.fiftyTwoWeekHigh), numberOrNull(quote.fifty_two_week_high)),"),
    ("fifty_two_week_low: Number(raw(sd.fiftyTwoWeekLow)),", "fifty_two_week_low: firstFinite(numberOrNull(sd.fiftyTwoWeekLow), numberOrNull(quote.fifty_two_week_low)),"),
    ("beta: Number(raw(ks.beta)),", "beta: numberOrNull(ks.beta),"),
]
for old, new in replacements:
    s = once(s, old, new, old[:48])

s = once(s, 'version: "4.4",', 'version: "4.5",', "health version")
s = once(
    s,
    "market_cache_ttl_seconds: MARKET_CACHE_TTL\n",
    "market_cache_ttl_seconds: MARKET_CACHE_TTL,\n          missing_numeric_policy: \"null\"\n",
    "health missing numeric policy",
)
s = once(s, 'service: "Vestra Market Proxy v4.4",', 'service: "Vestra Market Proxy v4.5",', "root version")

path.write_text(s, encoding="utf-8")


test = Path("tests/test_worker_missing_numeric_semantics.py")
test.write_text('''from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class WorkerMissingNumericSemanticsTests(unittest.TestCase):
    def test_null_safe_numeric_helper_prevents_number_null_zero_coercion(self):
        worker = read("worker.js")
        self.assertIn("function numberOrNull(node)", worker)
        self.assertIn("if (value === null || value === undefined || value === '') return null", worker)
        self.assertIn("const v = numberOrNull(node)", worker)
        self.assertNotIn("const v = Number(raw(node))", worker)
        self.assertNotIn("const n = Number(raw(v))", worker)

    def test_market_payload_uses_null_safe_numeric_reads(self):
        worker = read("worker.js")
        self.assertIn("const marketCap = firstFinite(numberOrNull(price.marketCap)", worker)
        self.assertIn("analyst_price_target_mean: target !== null && target > 0 ? target : null", worker)
        self.assertIn("current_ratio: numberOrNull(fd.currentRatio)", worker)
        self.assertIn("beta: numberOrNull(ks.beta)", worker)
        self.assertIn("missing_numeric_policy: \"null\"", worker)

    def test_missing_chart_closes_are_not_serialized_as_zero(self):
        worker = read("worker.js")
        self.assertIn("const close = numberOrNull(closes[i])", worker)
        self.assertIn("close !== null && close > 0", worker)
        self.assertNotIn("close:Number(closes[i])", worker)

    def test_new_market_cache_generation_does_not_reuse_zero_coerced_payloads(self):
        worker = read("worker.js")
        self.assertIn("market45:${canonical}", worker)
        self.assertNotIn("market41:${canonical}", worker)


if __name__ == "__main__":
    unittest.main(verbosity=2)
''', encoding="utf-8")
