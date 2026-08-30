from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
score = ROOT / 'scripts' / 'score_forward_validation.py'
ui = ROOT / 'market-model-validation.js'
test_score = ROOT / 'tests' / 'test_score_forward_validation_persistence.py'
test_ui = ROOT / 'tests' / 'test_market_model_validation.py'

text = score.read_text(encoding='utf-8')
anchor = """def expected_matured_count(today, snapshots, horizon):\n    count = 0\n    for snap in snapshots:\n        try:\n            age = (today - dt.date.fromisoformat(snap[\"date\"])).days\n        except Exception:\n            continue\n        if age >= horizon:\n            count += 1\n    return count\n\n\ndef main():"""
replacement = """def expected_matured_count(today, snapshots, horizon):\n    count = 0\n    for snap in snapshots:\n        try:\n            age = (today - dt.date.fromisoformat(snap[\"date\"])).days\n        except Exception:\n            continue\n        if age >= horizon:\n            count += 1\n    return count\n\n\ndef maturity_dates(today, snapshots, horizon):\n    dates = []\n    for snap in snapshots:\n        try:\n            dates.append(dt.date.fromisoformat(snap[\"date\"]))\n        except Exception:\n            continue\n    if not dates:\n        return None, None\n    maturity = sorted(d + dt.timedelta(days=horizon) for d in dates)\n    first = maturity[0]\n    pending = [d for d in maturity if d > today]\n    return first, (pending[0] if pending else None)\n\n\ndef main():"""
if anchor not in text:
    raise SystemExit('maturity function anchor not found')
text = text.replace(anchor, replacement, 1)

old = """        expected = expected_matured_count(today, snapshots, horizon)\n        report_horizons[str(horizon)] = summarize_horizon(vals, expected)"""
new = """        expected = expected_matured_count(today, snapshots, horizon)\n        summary = summarize_horizon(vals, expected)\n        first_maturity, next_maturity = maturity_dates(today, snapshots, horizon)\n        summary[\"first_possible_maturity_date\"] = first_maturity.isoformat() if first_maturity else None\n        summary[\"next_pending_maturity_date\"] = next_maturity.isoformat() if next_maturity else None\n        report_horizons[str(horizon)] = summary"""
if old not in text:
    raise SystemExit('report loop anchor not found')
text = text.replace(old, new, 1)
score.write_text(text, encoding='utf-8')

text = ui.read_text(encoding='utf-8')
old = """    const medianIc = data.median_cohort_rank_ic ?? data.rank_information_coefficient;\n    const medianSpread = data.median_cohort_top_minus_bottom_pct ?? data.top_minus_bottom_pct;\n    const cohortLabel = expectedCohorts !== null && expectedCohorts > 0"""
new = """    const medianIc = data.median_cohort_rank_ic ?? data.rank_information_coefficient;\n    const medianSpread = data.median_cohort_top_minus_bottom_pct ?? data.top_minus_bottom_pct;\n    const nextMaturity = data.next_pending_maturity_date;\n    const cohortLabel = expectedCohorts !== null && expectedCohorts > 0"""
if old not in text:
    raise SystemExit('UI variables anchor not found')
text = text.replace(old, new, 1)
old = """        <div class=\"model-validation-card__foot\">${cohortCount < 4 ? 'Ainda sem cohorts independentes suficientes para interpretar.' : cohortCount < 8 ? 'Sinal preliminar; não usar para recalibrar pesos.' : 'Base mínima de cohorts atingida; confirmar noutro horizonte antes de calibrar.'}</div>"""
new = """        <div class=\"model-validation-card__foot\">${cohortCount < 4 ? (nextMaturity ? `Próxima maturação prevista: ${dateLabel(nextMaturity)}. Ainda sem cohorts independentes suficientes para interpretar.` : 'Ainda sem cohorts independentes suficientes para interpretar.') : cohortCount < 8 ? 'Sinal preliminar; não usar para recalibrar pesos.' : 'Base mínima de cohorts atingida; confirmar noutro horizonte antes de calibrar.'}</div>"""
if old not in text:
    raise SystemExit('UI footer anchor not found')
text = text.replace(old, new, 1)
ui.write_text(text, encoding='utf-8')

text = test_score.read_text(encoding='utf-8')
anchor = """    def test_factor_diagnostics_are_exposed(self):"""
addition = """    def test_maturity_dates_expose_first_and_next_checkpoint(self):\n        today = dt.date(2026, 8, 30)\n        snapshots = [{\"date\": \"2026-08-27\", \"observations\": {}}, {\"date\": \"2026-09-03\", \"observations\": {}}]\n        first, pending = MOD.maturity_dates(today, snapshots, 28)\n        self.assertEqual(first, dt.date(2026, 9, 24))\n        self.assertEqual(pending, dt.date(2026, 9, 24))\n\n""" + anchor
if anchor not in text:
    raise SystemExit('score test anchor not found')
text = text.replace(anchor, addition, 1)
test_score.write_text(text, encoding='utf-8')

text = test_ui.read_text(encoding='utf-8')
anchor = """    def test_schema_v1_remains_a_safe_read_fallback(self):"""
addition = """    def test_panel_exposes_next_maturity_checkpoint(self):\n        text = MODULE.read_text(encoding=\"utf-8\")\n        self.assertIn(\"next_pending_maturity_date\", text)\n        self.assertIn(\"Próxima maturação prevista\", text)\n\n""" + anchor
if anchor not in text:
    raise SystemExit('UI test anchor not found')
text = text.replace(anchor, addition, 1)
test_ui.write_text(text, encoding='utf-8')
