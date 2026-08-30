from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'app.js'
TEST = ROOT / 'tests' / 'test_quote_refresh_diagnostics.py'
text = APP.read_text(encoding='utf-8')

old = '''async function fetchQuoteWithFallback(ref) {\n  let lastErr = null;\n  for (const candidate of (ref.candidates || [])) {\n    try {\n      if (!isQuoteCandidateAcceptable(ref.asset, candidate)) {\n        lastErr = new Error(`Candidato incompatível com a identidade do ativo: ${candidate}`);\n        continue;\n      }\n      const q = await fetchQuote(candidate, workerUrl);\n      if (q && Number.isFinite(Number(q.price)) && Number(q.price) > 0) {\n        return { yahoo: candidate, quote: q };\n      }\n      lastErr = new Error(`Sem dados para ${candidate}`);\n    } catch (e) {\n      lastErr = e;\n    }\n  }\n  throw lastErr || new Error("Não foi possível obter uma cotação válida");\n}\n'''
new = '''async function fetchQuoteWithFallback(ref) {\n  let lastErr = null;\n  let attempts = 0;\n  const startedAt = performance.now();\n  for (const candidate of (ref.candidates || [])) {\n    attempts += 1;\n    try {\n      if (!isQuoteCandidateAcceptable(ref.asset, candidate)) {\n        lastErr = new Error(`Candidato incompatível com a identidade do ativo: ${candidate}`);\n        continue;\n      }\n      const q = await fetchQuote(candidate, workerUrl);\n      if (q && Number.isFinite(Number(q.price)) && Number(q.price) > 0) {\n        return { yahoo: candidate, quote: q, attempts, durationMs: Math.round(performance.now() - startedAt) };\n      }\n      lastErr = new Error(`Sem dados para ${candidate}`);\n    } catch (e) {\n      lastErr = e;\n    }\n  }\n  const outErr = lastErr || new Error("Não foi possível obter uma cotação válida");\n  try {\n    outErr.quoteAttempts = attempts;\n    outErr.quoteDurationMs = Math.round(performance.now() - startedAt);\n  } catch (_) {}\n  throw outErr;\n}\n'''
if old not in text:
    raise SystemExit('fetchQuoteWithFallback anchor not found')
text = text.replace(old, new, 1)

old = '''  const quoteResults = await mapWithConcurrency(tickerList, 8, x => fetchQuoteWithFallback(x));\n  const quoteMap = {};\n  const quoteErrMap = {};\n  quoteResults.forEach((r, i) => {\n    if (r && r.status === "fulfilled" && r.value && r.value.quote) quoteMap[i] = r.value;\n    else quoteErrMap[i] = (r && r.reason && r.reason.message) ? r.reason.message : "Erro ao obter cotação";\n'''
new = '''  const quoteResults = await mapWithConcurrency(tickerList, 8, x => fetchQuoteWithFallback(x));\n  const quoteMap = {};\n  const quoteErrMap = {};\n  const quotePerformanceRows = quoteResults.map((r, i) => {\n    const ref = tickerList[i] || {};\n    if (r && r.status === "fulfilled" && r.value) {\n      return {\n        ticker: r.value.yahoo || ref.raw || "",\n        attempts: Number(r.value.attempts || 1),\n        durationMs: Number(r.value.durationMs || 0),\n        success: true\n      };\n    }\n    return {\n      ticker: ref.raw || "",\n      attempts: Number((r && r.reason && r.reason.quoteAttempts) || 0),\n      durationMs: Number((r && r.reason && r.reason.quoteDurationMs) || 0),\n      success: false\n    };\n  });\n  const fallbackAssets = quotePerformanceRows.filter(x => x.attempts > 1).length;\n  const maxCandidateAttempts = quotePerformanceRows.length ? Math.max(...quotePerformanceRows.map(x => x.attempts || 0)) : 0;\n  const meanDurationMs = quotePerformanceRows.length\n    ? Math.round(quotePerformanceRows.reduce((sum, x) => sum + (x.durationMs || 0), 0) / quotePerformanceRows.length)\n    : 0;\n  const slowestAssets = [...quotePerformanceRows]\n    .sort((a, b) => (b.durationMs || 0) - (a.durationMs || 0))\n    .slice(0, 5);\n  quoteResults.forEach((r, i) => {\n    if (r && r.status === "fulfilled" && r.value && r.value.quote) quoteMap[i] = r.value;\n    else quoteErrMap[i] = (r && r.reason && r.reason.message) ? r.reason.message : "Erro ao obter cotação";\n'''
if old not in text:
    raise SystemExit('quoteResults anchor not found')
text = text.replace(old, new, 1)

old = '''  state.settings.lastQuoteRefresh = { updated, failed, skipped, errors, workerMode:"individual", ts: new Date().toISOString(), durationMs: Math.round(performance.now() - refreshStartedAt) };\n'''
new = '''  state.settings.lastQuoteRefresh = {\n    updated, failed, skipped, errors, workerMode:"individual",\n    ts: new Date().toISOString(),\n    durationMs: Math.round(performance.now() - refreshStartedAt),\n    performance: {\n      assets: quotePerformanceRows.length,\n      fallbackAssets,\n      maxCandidateAttempts,\n      meanDurationMs,\n      slowestAssets\n    }\n  };\n'''
if old not in text:
    raise SystemExit('lastQuoteRefresh anchor not found')
text = text.replace(old, new, 1)

old = '''    meta.textContent = `${report.updated || 0} atualizadas · ${report.failed} com erro${skipped}${mode}${secs}`;\n'''
new = '''    const fallback = Number(report?.performance?.fallbackAssets || 0);\n    const fallbackLabel = fallback > 0 ? ` · ${fallback} com fallback` : "";\n    meta.textContent = `${report.updated || 0} atualizadas · ${report.failed} com erro${skipped}${mode}${fallbackLabel}${secs}`;\n'''
if old not in text:
    raise SystemExit('error status anchor not found')
text = text.replace(old, new, 1)

old = '''    meta.textContent = `${report.updated} atualizadas${skipped}${mode}${secs} · automático`;\n'''
new = '''    const fallback = Number(report?.performance?.fallbackAssets || 0);\n    const fallbackLabel = fallback > 0 ? ` · ${fallback} com fallback` : "";\n    meta.textContent = `${report.updated} atualizadas${skipped}${mode}${fallbackLabel}${secs} · automático`;\n'''
if old not in text:
    raise SystemExit('success status anchor not found')
text = text.replace(old, new, 1)

APP.write_text(text, encoding='utf-8')

TEST.write_text('''from pathlib import Path\nimport subprocess\nimport unittest\n\nROOT = Path(__file__).resolve().parents[1]\nAPP = ROOT / "app.js"\n\nclass QuoteRefreshDiagnosticsTests(unittest.TestCase):\n    def test_app_js_is_valid(self):\n        subprocess.run(["node", "--check", str(APP)], check=True, cwd=ROOT)\n\n    def test_fallback_attempts_are_measured_without_changing_identity_policy(self):\n        text = APP.read_text(encoding="utf-8")\n        self.assertIn("let attempts = 0", text)\n        self.assertIn("durationMs: Math.round(performance.now() - startedAt)", text)\n        self.assertIn("outErr.quoteAttempts = attempts", text)\n        self.assertIn("isQuoteCandidateAcceptable(ref.asset, candidate)", text)\n        self.assertIn("for (const candidate of (ref.candidates || []))", text)\n\n    def test_refresh_report_persists_compact_performance_diagnostics(self):\n        text = APP.read_text(encoding="utf-8")\n        for token in (\n            "quotePerformanceRows", "fallbackAssets", "maxCandidateAttempts",\n            "meanDurationMs", "slowestAssets", "performance: {"\n        ):\n            self.assertIn(token, text)\n        self.assertIn("com fallback", text)\n        self.assertIn("QUOTE_AUTO_REFRESH_STALE_MS = 60 * 1000", text)\n\n    def test_diagnostics_do_not_parallel_race_candidates(self):\n        text = APP.read_text(encoding="utf-8")\n        self.assertNotIn("Promise.any(ref.candidates", text)\n        self.assertNotIn("Promise.race(ref.candidates", text)\n\nif __name__ == "__main__":\n    unittest.main(verbosity=2)\n''', encoding='utf-8')
