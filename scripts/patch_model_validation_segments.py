from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ui = ROOT / 'market-model-validation.js'
test = ROOT / 'tests' / 'test_market_model_validation.py'

text = ui.read_text(encoding='utf-8')
anchor = """  function render(payload) {\n    const horizons = payload.horizons || {};"""
insert = """  function segmentDiagnostics(payload) {\n    const rows = [];\n    for (const days of ['28', '84', '168']) {\n      const horizon = payload?.horizons?.[days] || {};\n      for (const [kind, source] of [['Modelo', horizon.by_score_model], ['Setor', horizon.by_sector]]) {\n        if (!source || typeof source !== 'object') continue;\n        for (const [name, stats] of Object.entries(source)) {\n          if (!stats || typeof stats !== 'object') continue;\n          const n = finite(stats.n) ?? 0;\n          const ic = finite(stats.median_cohort_rank_ic ?? stats.rank_information_coefficient);\n          const spread = finite(stats.median_cohort_top_minus_bottom_pct ?? stats.top_minus_bottom_pct);\n          if (n < 20 && ic === null && spread === null) continue;\n          rows.push({ kind, name, days: Number(days), n, ic, spread });\n        }\n      }\n    }\n    if (!rows.length) return '';\n    rows.sort((a, b) => (b.days - a.days) || (b.n - a.n) || a.name.localeCompare(b.name));\n    const selected = rows.slice(0, 12);\n    return `<div class=\"model-validation-section\"><h4>Por modelo e setor</h4><div class=\"model-validation-segments\">${selected.map(row => `<div class=\"model-validation-segment\"><div><small>${esc(row.kind)} · ${row.days}d</small><strong>${esc(row.name)}</strong></div><div><small>n</small><strong>${row.n}</strong></div><div><small>Rank IC</small><strong>${signed(row.ic,3)}</strong></div><div><small>Top − Bottom</small><strong>${signed(row.spread,2,'%')}</strong></div></div>`).join('')}</div><div class=\"model-validation-meta\">Amostras segmentadas pequenas são apenas diagnósticas; não servem para recalibrar pesos isoladamente.</div></div>`;\n  }\n\n  function render(payload) {\n    const horizons = payload.horizons || {};"""
if anchor not in text:
    raise SystemExit('render anchor not found')
text = text.replace(anchor, insert, 1)

old_style = ".model-validation-empty{padding:22px;border:1px dashed var(--border,#dfe5e2);border-radius:16px;text-align:center;color:var(--muted,#6d7a75);font-size:12px;line-height:1.5}.model-validation-meta{margin-top:14px;color:var(--muted,#6d7a75);font-size:10px}"
new_style = old_style + ".model-validation-segments{display:grid;gap:7px}.model-validation-segment{display:grid;grid-template-columns:minmax(130px,1.5fr) 50px 78px 92px;gap:10px;align-items:center;padding:9px 10px;border:1px solid var(--border,#e0e6e3);border-radius:12px;background:var(--surface-2,#f7f9f8);font-size:11px}.model-validation-segment small{display:block;color:var(--muted,#6d7a75);font-size:9px;margin-bottom:2px}.model-validation-segment strong{font-size:11px}"
if old_style not in text:
    raise SystemExit('style anchor not found')
text = text.replace(old_style, new_style, 1)

old_mobile = "@media(max-width:640px){.model-validation-overlay{padding:0}.model-validation-sheet{max-height:92vh;border-radius:24px 24px 0 0}.model-validation-summary{grid-template-columns:1fr}.model-validation-factor{grid-template-columns:minmax(105px,1fr) 58px 1fr}.model-validation-head,.model-validation-body{padding-left:16px;padding-right:16px}}"
new_mobile = "@media(max-width:640px){.model-validation-overlay{padding:0}.model-validation-sheet{max-height:92vh;border-radius:24px 24px 0 0}.model-validation-summary{grid-template-columns:1fr}.model-validation-factor{grid-template-columns:minmax(105px,1fr) 58px 1fr}.model-validation-segment{grid-template-columns:minmax(120px,1.4fr) 36px 62px 76px;gap:7px}.model-validation-head,.model-validation-body{padding-left:16px;padding-right:16px}}"
if old_mobile not in text:
    raise SystemExit('mobile anchor not found')
text = text.replace(old_mobile, new_mobile, 1)

old_render = """        <div class=\"model-validation-section\"><h4>Leitura dos pilares</h4>${factorDiagnostics(payload)}</div>\n        <div class=\"model-validation-section\"><h4>Como interpretar</h4>"""
new_render = """        <div class=\"model-validation-section\"><h4>Leitura dos pilares</h4>${factorDiagnostics(payload)}</div>\n        ${segmentDiagnostics(payload)}\n        <div class=\"model-validation-section\"><h4>Como interpretar</h4>"""
if old_render not in text:
    raise SystemExit('render body anchor not found')
text = text.replace(old_render, new_render, 1)
ui.write_text(text, encoding='utf-8')

base = test.read_text(encoding='utf-8') if test.exists() else ''
if 'test_panel_exposes_model_and_sector_diagnostics' not in base:
    marker = 'if __name__ == "__main__":\n'
    addition = '''    def test_panel_exposes_model_and_sector_diagnostics(self):\n        text = MODULE.read_text(encoding="utf-8")\n        self.assertIn("segmentDiagnostics", text)\n        self.assertIn("by_score_model", text)\n        self.assertIn("by_sector", text)\n        self.assertIn("Por modelo e setor", text)\n        self.assertIn("Amostras segmentadas pequenas", text)\n\n'''
    if marker in base:
        base = base.replace(marker, addition + marker, 1)
    else:
        base += '\n' + addition
    test.write_text(base, encoding='utf-8')
