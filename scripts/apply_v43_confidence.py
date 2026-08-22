from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path, old, new):
    p = ROOT / path
    s = p.read_text(encoding='utf-8')
    if new in s:
        return
    if old not in s:
        raise RuntimeError(f'anchor missing in {path}: {old[:80]!r}')
    p.write_text(s.replace(old, new, 1), encoding='utf-8')

# SEC: expose freshness + independent-source agreement when like-for-like values exist.
replace_once(
    'scripts/sec_enrich.py',
    "def enrich(raw, priority=None, max_nonpriority=350):\n",
    '''def _latest_period_end(facts):\n    ends=[]\n    us=facts.get('us-gaap',{})\n    for tags in _TAGS.values():\n        for tag in tags:\n            node=us.get(tag,{})\n            for rows in (node.get('units') or {}).values():\n                for r in rows:\n                    if r.get('form') in ('10-K','10-Q','20-F','40-F','6-K') and r.get('end'):\n                        ends.append(str(r.get('end')))\n    return max(ends) if ends else None\n\n\ndef _agreement(old, new, tolerance=0.25):\n    try:\n        if old is None or new is None:\n            return None\n        a=float(old); b=float(new)\n        scale=max(abs(a),abs(b),1.0)\n        return abs(a-b)/scale <= tolerance\n    except Exception:\n        return None\n\n\ndef enrich(raw, priority=None, max_nonpriority=350):\n'''
)

replace_once(
    'scripts/sec_enrich.py',
    "            debt=sum(x or 0 for x in [_latest(facts,(_TAGS['debt'][0],)),_latest(facts,(_TAGS['debt'][1],)),_latest(facts,(_TAGS['debt'][2],)),_latest(facts,(_TAGS['debt'][3],))]) or None\n",
    """            debt=sum(x or 0 for x in [_latest(facts,(_TAGS['debt'][0],)),_latest(facts,(_TAGS['debt'][1],)),_latest(facts,(_TAGS['debt'][2],)),_latest(facts,(_TAGS['debt'][3],))]) or None\n            setattr(m,'sec_period_end',_latest_period_end(facts))\n            sec_current_ratio=(ac/lc) if ac is not None and lc not in (None,0) else None\n            checks=[]\n            for old,new,tol in (\n                (getattr(m,'total_cash',None),cash,0.30),\n                (getattr(m,'total_debt',None),debt,0.30),\n                (getattr(m,'current_ratio',None),sec_current_ratio,0.20),\n                (getattr(m,'total_assets',None),assets,0.20),\n                (getattr(m,'stockholders_equity',None),eq,0.20),\n            ):\n                ok=_agreement(old,new,tol)\n                if ok is not None: checks.append(ok)\n            setattr(m,'source_agreement_checks',len(checks))\n            setattr(m,'source_agreement_pct',round(sum(1 for x in checks if x)/len(checks)*100,1) if checks else None)\n"""
)

# Pipeline: run v4.3 confidence after provenance is assembled, before thesis classification.
replace_once(
    'scripts/run.py',
    'from capital_risk import enrich as enrich_capital_risk\n',
    'from capital_risk import enrich as enrich_capital_risk\nfrom confidence import assess as assess_confidence\n'
)
replace_once(
    'scripts/run.py',
    'for _name in ("run", "universe", "fundamentals", "sec_enrich", "esef_enrich", "analyst",',
    'for _name in ("run", "universe", "fundamentals", "sec_enrich", "esef_enrich", "confidence", "analyst",'
)
replace_once(
    'scripts/run.py',
    '        if rm is not None and getattr(rm, "sec_edgar_enriched", False): row["data_sources"].append("SEC EDGAR")\n',
    '        if rm is not None and getattr(rm, "sec_edgar_enriched", False):\n            row["data_sources"].append("SEC EDGAR")\n            row["sec_period_end"] = getattr(rm, "sec_period_end", None)\n            row["source_agreement_checks"] = getattr(rm, "source_agreement_checks", 0)\n            row["source_agreement_pct"] = getattr(rm, "source_agreement_pct", None)\n'
)
replace_once(
    'scripts/run.py',
    '            row["repurchases_last_quarter"] = rm.repurchases_last_quarter\n        row.update(classify_thesis(row))\n',
    '            row["repurchases_last_quarter"] = rm.repurchases_last_quarter\n        row.update(assess_confidence(row))\n        row.update(classify_thesis(row))\n'
)
replace_once('scripts/run.py', '"schema_version": 512,', '"schema_version": 513,')

# Thesis confidence now consumes the evidence-confidence engine instead of raw coverage alone.
replace_once(
    'scripts/thesis.py',
    '''    if coverage is None or coverage < 40:\n        confidence = "low"\n    elif coverage >= 70 and len(evidence) >= 2:\n        confidence = "high"\n    else:\n        confidence = "medium"\n''',
    '''    confidence_score = _n(row.get("confidence_score"))\n    if confidence_score is not None:\n        if confidence_score >= 80 and (len(evidence) >= 2 or row.get("risk_gate") in ("high", "severe")):\n            confidence = "high"\n        elif confidence_score >= 60:\n            confidence = "medium"\n        else:\n            confidence = "low"\n    elif coverage is None or coverage < 40:\n        confidence = "low"\n    elif coverage >= 70 and len(evidence) >= 2:\n        confidence = "high"\n    else:\n        confidence = "medium"\n'''
)

# Release notes and cache only; no layout changes.
p=ROOT/'README.md'
s=p.read_text(encoding='utf-8')
head='''## Vestra v4.3 — Confidence Engine\n\n- “Confiança” deixa de ser sinónimo de quantidade de campos preenchidos.\n- Novo Confidence Score 0–100 combina cobertura, autoridade/diversidade das fontes, frescura das contas, concordância entre fontes e robustez da identidade.\n- SEC EDGAR expõe a data do período mais recente e cross-checks like-for-like de caixa, dívida, current ratio, ativos e equity quando Yahoo também tem esses valores.\n- Divergência relevante entre fontes impede confiança alta; contas muito antigas também limitam a confiança.\n- A confiança da tese passa a usar o Confidence Engine e pode ser alta tanto para uma boa tese como para um risco estrutural bem confirmado.\n- `metric_confidence` preserva a antiga leitura baseada apenas em cobertura para auditoria.\n- Layout visual permanece congelado.\n- PWA cache: `vestra-cache-v36`.\n\n'''
if not s.startswith('## Vestra v4.3'):
    p.write_text(head+s,encoding='utf-8')

replace_once('sw.js','/* Vestra — Service Worker v4.2 */','/* Vestra — Service Worker v4.3 */')
replace_once('sw.js','const CACHE_NAME = "vestra-cache-v35";','const CACHE_NAME = "vestra-cache-v36";')
