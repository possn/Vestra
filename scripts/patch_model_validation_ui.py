from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
module = ROOT / 'market-model-validation.js'
test = ROOT / 'tests' / 'test_market_model_validation.py'

text = module.read_text(encoding='utf-8')
old = """  const finite = value => {\n    const number = Number(value);\n    return Number.isFinite(number) ? number : null;\n  };"""
new = """  const finite = value => {\n    if (value === null || value === undefined || value === '') return null;\n    const number = Number(value);\n    return Number.isFinite(number) ? number : null;\n  };"""
if old not in text:
    raise SystemExit('finite helper anchor not found')
text = text.replace(old, new, 1)

old = """    const cohortCount = finite(data.cohort_count) ?? 0;\n    const n = finite(data.n) ?? 0;\n    const medianIc = data.median_cohort_rank_ic ?? data.rank_information_coefficient;\n    const medianSpread = data.median_cohort_top_minus_bottom_pct ?? data.top_minus_bottom_pct;"""
new = """    const cohortCount = finite(data.cohort_count) ?? 0;\n    const expectedCohorts = finite(data.expected_matured_cohorts);\n    const capturePct = finite(data.cohort_capture_pct);\n    const n = finite(data.n) ?? 0;\n    const medianIc = data.median_cohort_rank_ic ?? data.rank_information_coefficient;\n    const medianSpread = data.median_cohort_top_minus_bottom_pct ?? data.top_minus_bottom_pct;\n    const cohortLabel = expectedCohorts !== null && expectedCohorts > 0\n      ? `${cohortCount}/${expectedCohorts}${capturePct !== null ? ` · ${capturePct.toFixed(0)}%` : ''}`\n      : String(cohortCount);"""
if old not in text:
    raise SystemExit('horizon variables anchor not found')
text = text.replace(old, new, 1)
text = text.replace('<div class="model-validation-metric"><small>Cohorts maturados</small><strong>${cohortCount}</strong></div>', '<div class="model-validation-metric"><small>Cohorts maturados / esperados</small><strong>${cohortLabel}</strong></div>', 1)
module.write_text(text, encoding='utf-8')

text = test.read_text(encoding='utf-8')
anchor = """    def test_schema_v1_remains_a_safe_read_fallback(self):\n        text = MODULE.read_text(encoding=\"utf-8\")\n        self.assertIn(\"data.median_cohort_rank_ic ?? data.rank_information_coefficient\", text)\n        self.assertIn(\"data.median_cohort_top_minus_bottom_pct ?? data.top_minus_bottom_pct\", text)\n"""
addition = anchor + """\n    def test_missing_validation_numbers_never_become_zero(self):\n        text = MODULE.read_text(encoding=\"utf-8\")\n        self.assertIn(\"value === null || value === undefined || value === ''\", text)\n        self.assertIn(\"expected_matured_cohorts\", text)\n        self.assertIn(\"cohort_capture_pct\", text)\n        self.assertIn(\"Cohorts maturados / esperados\", text)\n"""
if anchor not in text:
    raise SystemExit('test anchor not found')
text = text.replace(anchor, addition, 1)
test.write_text(text, encoding='utf-8')
