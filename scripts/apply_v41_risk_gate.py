from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path, old, new):
    p = ROOT / path
    s = p.read_text(encoding='utf-8')
    if new in s:
        return
    if old not in s:
        raise RuntimeError(f'anchor missing in {path}')
    p.write_text(s.replace(old, new, 1), encoding='utf-8')

# 1) Add auditable risk-gate fields to ScoredTicker.
replace_once(
    'scripts/score.py',
    '    score_model: str = "general"\n    score_model_note: str | None = None\n    score_dimensions: dict[str, float | None] | None = None\n',
    '    score_model: str = "general"\n    score_model_note: str | None = None\n    score_dimensions: dict[str, float | None] | None = None\n    risk_flags: list[str] | None = None\n    risk_gate: str = "clear"\n    score_cap: float | None = None\n'
)

# 2) Extreme FCF yield is an anomaly, not an automatic positive factor.
replace_once(
    'scripts/score.py',
    '        fcf_yield = fcf_yields[idx]\n        cashflow = _avg([\n            _percentile_rank(fcf_yield, fcf_yields),\n            _positive_score(r.operating_cash_flow),\n        ])\n',
    '        fcf_yield = fcf_yields[idx]\n        # Extremely high FCF yields are often distress/data/capital-structure signals.\n        # Do not reward >30% automatically until an independent source confirms it.\n        fcf_yield_for_score = fcf_yield if fcf_yield is None or abs(fcf_yield) <= 0.30 else None\n        plausible_fcf_yields = [v if v is None or abs(v) <= 0.30 else None for v in fcf_yields]\n        cashflow = _avg([\n            _percentile_rank(fcf_yield_for_score, plausible_fcf_yields),\n            _positive_score(r.operating_cash_flow),\n        ])\n'
)

# 3) Add the post-score Risk Gate before the legacy zombie cap.
replace_once(
    'scripts/score.py',
    '        if model != "general":\n            execution = None\n            earnings_quality = None\n            capital_allocation = None\n\n        if composite is not None and zombie == "yes" and model not in ("bank", "insurance"):\n            composite = min(composite, 45.0)\n',
    '        if model != "general":\n            execution = None\n            earnings_quality = None\n            capital_allocation = None\n\n        # v4.1 Risk Gate: weighted averages cannot wash away structural red flags.\n        # The flags are deliberately generic and explainable; no ticker blacklist.\n        risk_flags = []\n        if zombie == "yes" and model not in ("bank", "insurance"):\n            risk_flags.append("zombie_interest_coverage")\n        if fcf_yield is not None and abs(fcf_yield) > 0.30:\n            risk_flags.append("extreme_fcf_yield")\n        if quality is not None and quality < 40:\n            risk_flags.append("weak_quality")\n        if r.revenue_growth is not None and r.revenue_growth < -0.15:\n            risk_flags.append("revenue_contraction")\n        if r.diluted_shares_yoy is not None and r.diluted_shares_yoy > 0.20:\n            risk_flags.append("material_dilution")\n        if r.diluted_shares_yoy is not None and r.diluted_shares_yoy > 0.50:\n            risk_flags.append("severe_dilution")\n\n        risk_gate = "clear"\n        score_cap = None\n        severe = any(x in risk_flags for x in ("zombie_interest_coverage", "severe_dilution"))\n        if severe:\n            risk_gate, score_cap = "severe", 45.0\n        elif len(risk_flags) >= 2:\n            risk_gate, score_cap = "high", 59.0\n        elif risk_flags:\n            risk_gate, score_cap = "watch", 69.0\n        if composite is not None and score_cap is not None:\n            composite = min(composite, score_cap)\n'
)

# 4) Confidence is not merely completeness when the data themselves are anomalous.
replace_once(
    'scripts/score.py',
    '        confidence = "high" if metric_coverage >= 70 else "medium" if metric_coverage >= 40 else "low"\n        if model == "bank" and confidence == "high":\n',
    '        confidence = "high" if metric_coverage >= 70 else "medium" if metric_coverage >= 40 else "low"\n        if risk_gate == "severe":\n            confidence = "low"\n        elif risk_gate == "high" and confidence == "high":\n            confidence = "medium"\n        if model == "bank" and confidence == "high":\n'
)

# 5) Persist the gate into stocks.json.
replace_once(
    'scripts/score.py',
    '            score_model=model, score_model_note=model_note, score_dimensions=score_dimensions,\n',
    '            score_model=model, score_model_note=model_note, score_dimensions=score_dimensions,\n            risk_flags=risk_flags, risk_gate=risk_gate, score_cap=score_cap,\n'
)

# 6) Bump methodology wording and release notes; no layout changes.
p = ROOT / 'README.md'
s = p.read_text(encoding='utf-8')
head = '''## Vestra v4.1 — Risk Gate\n\n- O score quantitativo passa por um Risk Gate antes de gerar o sinal final.\n- FCF yield extremo (>30%) deixa de receber automaticamente um percentil favorável sem confirmação independente.\n- Zombie por interest coverage, qualidade muito fraca, contração relevante de receita e diluição material passam a limitar o score.\n- Dois ou mais red flags impedem um “Sinal forte”; red flags severos limitam o score a 45.\n- A confiança é reduzida quando existem anomalias materiais, mesmo com elevada cobertura de campos.\n- Nenhuma empresa é bloqueada por ticker/país: as regras são genéricas e auditáveis.\n- Layout visual permanece congelado.\n\n'''
if not s.startswith('## Vestra v4.1'):
    p.write_text(head + s, encoding='utf-8')

replace_once('sw.js', '/* Vestra — Service Worker v4.0 */', '/* Vestra — Service Worker v4.1 */')
replace_once('sw.js', 'const CACHE_NAME = "vestra-cache-v33";', 'const CACHE_NAME = "vestra-cache-v34";')
