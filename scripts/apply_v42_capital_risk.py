from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def one(path, old, new):
    p = ROOT / path
    s = p.read_text(encoding="utf-8")
    if new in s:
        return
    if old not in s:
        raise RuntimeError(f"anchor missing in {path}: {old[:80]!r}")
    p.write_text(s.replace(old, new, 1), encoding="utf-8")

# Pipeline: inspect SEC capital-structure events before scoring.
one("scripts/run.py", "from esef_enrich import enrich as enrich_esef\n", "from esef_enrich import enrich as enrich_esef\nfrom capital_risk import enrich as enrich_capital_risk\n")
one("scripts/run.py", '"fundamentals", "sec_enrich", "esef_enrich", "analyst"', '"fundamentals", "sec_enrich", "esef_enrich", "capital_risk", "analyst"')
one("scripts/run.py", "    raw = enrich_esef(raw, priority=portfolio_set)\n    scored = score_universe(raw)\n", "    raw = enrich_esef(raw, priority=portfolio_set)\n    raw = enrich_capital_risk(raw, priority=portfolio_set)\n    scored = score_universe(raw)\n")

# Persist capital-risk diagnostics and provenance in each company dossier row.
one(
    "scripts/run.py",
    '        if rm is not None:\n            if row.get("quote_type") == "ETF":\n',
    '        if rm is not None:\n            if getattr(rm, "capital_risk_checked", False):\n                row["data_sources"].append("SEC Capital Structure")\n                row["capital_structure_flags"] = getattr(rm, "capital_structure_flags", [])\n                row["capital_structure_risk"] = getattr(rm, "capital_structure_risk", "clear")\n                row["reverse_split_count_24m"] = getattr(rm, "reverse_split_count_24m", 0)\n                row["reverse_split_latest_date"] = getattr(rm, "reverse_split_latest_date", None)\n                row["capital_risk_filings_checked"] = getattr(rm, "capital_risk_filings_checked", 0)\n            if row.get("quote_type") == "ETF":\n'
)
one("scripts/run.py", '"schema_version": 511,', '"schema_version": 512,')

# Risk Gate: SEC capital-structure events are non-compensable red flags.
score_anchor = '''        if r.diluted_shares_yoy is not None and r.diluted_shares_yoy > 0.50:\n            risk_flags.append("severe_dilution")\n\n        risk_gate = "clear"\n        score_cap = None\n        severe = any(x in risk_flags for x in ("zombie_interest_coverage", "severe_dilution"))\n        if severe:\n            risk_gate, score_cap = "severe", 45.0\n        elif len(risk_flags) >= 2:\n            risk_gate, score_cap = "high", 59.0\n        elif risk_flags:\n            risk_gate, score_cap = "watch", 69.0\n        if composite is not None and score_cap is not None:\n            composite = min(composite, score_cap)\n'''
score_new = '''        if r.diluted_shares_yoy is not None and r.diluted_shares_yoy > 0.50:\n            risk_flags.append("severe_dilution")\n\n        capital_flags = list(getattr(r, "capital_structure_flags", []) or [])\n        for flag in capital_flags:\n            if flag not in risk_flags:\n                risk_flags.append(flag)\n        capital_gate = str(getattr(r, "capital_structure_risk", "clear") or "clear")\n\n        risk_gate = "clear"\n        score_cap = None\n        severe = any(x in risk_flags for x in ("zombie_interest_coverage", "severe_dilution"))\n        if severe:\n            risk_gate, score_cap = "severe", 45.0\n        elif len(risk_flags) >= 2:\n            risk_gate, score_cap = "high", 59.0\n        elif risk_flags:\n            risk_gate, score_cap = "watch", 69.0\n\n        # Filing-derived capital structure risk gets the most restrictive cap.\n        cap_by_gate = {"watch": 64.0, "high": 49.0, "severe": 35.0}\n        rank = {"clear": 0, "watch": 1, "high": 2, "severe": 3}\n        if capital_gate in cap_by_gate:\n            ccap = cap_by_gate[capital_gate]\n            score_cap = min(score_cap if score_cap is not None else 100.0, ccap)\n            if rank.get(capital_gate, 0) > rank.get(risk_gate, 0):\n                risk_gate = capital_gate\n        if composite is not None and score_cap is not None:\n            composite = min(composite, score_cap)\n'''
one("scripts/score.py", score_anchor, score_new)

# Thesis taxonomy: structural-risk names cannot still be presented as balanced/strong candidates.
one(
    "scripts/thesis.py",
    '    zombie = row.get("zombie") == "yes"\n\n    # Priority matters: explicit risk archetypes outrank superficially attractive scores.\n    if zombie or (v is not None and v >= 65 and ((q is not None and q < 40) or (g is not None and g < 30))):\n',
    '    zombie = row.get("zombie") == "yes"\n    risk_gate = str(row.get("risk_gate") or "clear")\n    capital_flags = list(row.get("capital_structure_flags") or [])\n\n    # Priority matters: structural-risk archetypes outrank superficially attractive scores.\n    if risk_gate in ("high", "severe"):\n        thesis_type, slug = "Capital Structure Risk", "capital-structure-risk"\n        summary = "A estrutura de capital ou os filings recentes mostram riscos que não devem ser compensados por valuation ou cash-flow aparentemente atrativos."\n    elif zombie or (v is not None and v >= 65 and ((q is not None and q < 40) or (g is not None and g < 30))):\n'
)

# Add translated filing risks to the existing risk list.
one(
    "scripts/thesis.py",
    '    if insider_net is not None and insider_net < -100_000:\n        risks.append("Fluxo líquido de insiders open-market negativo nos últimos 30 dias.")\n\n    # Keep the UI concise and deterministic.\n',
    '    if insider_net is not None and insider_net < -100_000:\n        risks.append("Fluxo líquido de insiders open-market negativo nos últimos 30 dias.")\n    capital_labels = {\n        "reverse_split_recent": "Reverse split identificado nos últimos 24 meses.",\n        "repeated_reverse_splits": "Reverse splits repetidos nos últimos 24 meses.",\n        "atm_offering": "Programa ATM / emissão contínua de ações identificado.",\n        "equity_financing": "Oferta de capital recente identificada nos filings.",\n        "convertible_financing": "Financiamento convertível recente identificado.",\n        "variable_price_convertible": "Convertível com preço variável/desconto ao mercado: risco elevado de diluição.",\n        "warrants_outstanding": "Warrants associados a financiamento/oferta identificados.",\n        "listing_compliance_risk": "Risco de cumprimento das regras de cotação/delisting identificado.",\n    }\n    for flag in capital_flags:\n        label = capital_labels.get(flag)\n        if label and label not in risks:\n            risks.append(label)\n\n    # Keep the UI concise and deterministic.\n'
)
one(
    "scripts/thesis.py",
    '    if coverage is None or coverage < 40:\n        confidence = "low"\n    elif coverage >= 70 and len(evidence) >= 2:\n',
    '    if risk_gate == "severe" or coverage is None or coverage < 40:\n        confidence = "low"\n    elif risk_gate == "high":\n        confidence = "medium"\n    elif coverage >= 70 and len(evidence) >= 2:\n'
)

# Release notes/cache only; no visual redesign.
p = ROOT / "README.md"
s = p.read_text(encoding="utf-8")
head = '''## Vestra v4.2 — Capital Structure & Corporate Actions Risk\n\n- SEC filings recentes passam a ser analisados para reverse splits, ATMs, ofertas de capital, convertíveis, warrants e risco de delisting.\n- Reverse splits repetidos e convertíveis com preço variável/desconto ao mercado tornam-se red flags estruturais.\n- O Risk Gate aplica caps não compensáveis: watch 64, high 49, severe 35.\n- A tese passa a usar “Capital Structure Risk” quando estes sinais dominam o caso de investimento.\n- O dossier recebe os eventos traduzidos em “O que pode quebrar a tese” através da taxonomia existente.\n- A recolha SEC é seletiva (micro/small caps, preços baixos, diluição/anomalias e posições prioritárias) para manter o pipeline rápido.\n- Sem blacklist por ticker ou país; regras auditáveis a partir dos filings.\n- Layout visual permanece congelado.\n- PWA cache: `vestra-cache-v35`.\n\n'''
if not s.startswith("## Vestra v4.2"):
    p.write_text(head + s, encoding="utf-8")

one("sw.js", "/* Vestra — Service Worker v4.1 */", "/* Vestra — Service Worker v4.2 */")
one("sw.js", 'const CACHE_NAME = "vestra-cache-v34";', 'const CACHE_NAME = "vestra-cache-v35";')
