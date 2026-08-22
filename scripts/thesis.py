"""Deterministic investment-thesis classifier for Finscanner.

This is a research taxonomy, not a recommendation engine. It converts the
already-calculated quantitative signals into an explainable archetype with
explicit supporting evidence and risks. Missing values never count as zero.
"""
from __future__ import annotations


def _n(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _pct(v):
    v = _n(v)
    return None if v is None else v * 100.0


def _add(items, condition, text):
    if condition:
        items.append(text)


def classify(row: dict) -> dict:
    if row.get("quote_type") == "ETF":
        return {
            "thesis_type": "ETF",
            "thesis_slug": "etf",
            "thesis_confidence": "medium",
            "thesis_summary": "Fundo cotado; a taxonomia de teses empresariais não se aplica diretamente.",
            "thesis_evidence": [],
            "thesis_risks": [],
        }

    q = _n(row.get("quality_pct"))
    g = _n(row.get("growth_pct"))
    b = _n(row.get("balance_pct"))
    cf = _n(row.get("cashflow_pct"))
    v = _n(row.get("value_pct"))
    score = _n(row.get("score"))
    rev_yoy = _pct(row.get("revenue_yoy_latest"))
    ni_yoy = _pct(row.get("net_income_yoy_latest"))
    dilution = _pct(row.get("diluted_shares_yoy"))
    margin_delta = _n(row.get("net_margin_yoy_change_pp"))
    debt_equity = _n(row.get("debt_to_equity"))
    insider_net = _n(row.get("insider_net_value_30d"))
    insider_buys = _n(row.get("insider_buy_count_30d")) or 0
    coverage = _n(row.get("data_coverage_pct"))
    zombie = row.get("zombie") == "yes"
    risk_gate = str(row.get("risk_gate") or "clear")
    capital_flags = list(row.get("capital_structure_flags") or [])

    # Priority matters: structural-risk archetypes outrank superficially attractive scores.
    if risk_gate in ("high", "severe"):
        thesis_type, slug = "Capital Structure Risk", "capital-structure-risk"
        summary = "A estrutura de capital ou os filings recentes mostram riscos que não devem ser compensados por valuation ou cash-flow aparentemente atrativos."
    elif zombie or (v is not None and v >= 65 and ((q is not None and q < 40) or (g is not None and g < 30))):
        thesis_type, slug = "Value Trap Risk", "value-trap"
        summary = "O valuation parece apelativo, mas a qualidade, crescimento ou solvência levantam risco de armadilha de valor."
    elif (g is not None and g >= 65 or (rev_yoy is not None and rev_yoy >= 20)) and dilution is not None and dilution >= 8:
        thesis_type, slug = "High Growth / High Dilution", "growth-dilution"
        summary = "Crescimento forte, mas com aumento material do número de ações; importa avaliar criação de valor por ação."
    elif (g is not None and g >= 65 or (rev_yoy is not None and rev_yoy >= 20)) and ((b is not None and b < 40) or (debt_equity is not None and debt_equity > 150)):
        thesis_type, slug = "Leveraged Growth", "leveraged-growth"
        summary = "A empresa cresce, mas a estrutura de capital é mais frágil do que o perfil operacional."
    elif q is not None and q >= 70 and g is not None and g >= 55 and cf is not None and cf >= 55 and b is not None and b >= 55 and (dilution is None or dilution <= 5):
        thesis_type, slug = "Quality Compounder", "compounder"
        summary = "Qualidade, crescimento, cash flow e balanço combinam-se num perfil de possível compounder."
    elif q is not None and q >= 60 and g is not None and g >= 60 and v is not None and v >= 55:
        thesis_type, slug = "GARP", "garp"
        summary = "Crescimento e qualidade acima da média sem exigir um valuation extremo relativamente ao universo."
    elif v is not None and v >= 75 and q is not None and q >= 45 and not zombie:
        thesis_type, slug = "Deep Value", "deep-value"
        summary = "Valuation muito favorável no universo atual, com qualidade suficiente para justificar investigação adicional."
    elif rev_yoy is not None and rev_yoy >= 10 and ni_yoy is not None and ni_yoy > 0 and margin_delta is not None and margin_delta >= 2:
        thesis_type, slug = "Turnaround", "turnaround"
        summary = "Receitas, lucros e margens estão a melhorar simultaneamente, compatível com uma recuperação operacional."
    elif insider_net is not None and insider_net >= 100_000 and insider_buys >= 2:
        thesis_type, slug = "Insider Accumulation", "insider-accumulation"
        summary = "Compras open-market de insiders criam um sinal adicional de alinhamento, sem substituir a análise fundamental."
    elif score is not None and score >= 65:
        thesis_type, slug = "Balanced Candidate", "balanced"
        summary = "Perfil multifator favorável, mas sem concentração suficiente de sinais para uma tese mais específica."
    else:
        thesis_type, slug = "Watch / No Edge", "watch"
        summary = "Os dados atuais não mostram uma vantagem quantitativa suficientemente clara para uma tese forte."

    evidence, risks = [], []
    if q is not None and q >= 65:
        evidence.append(f"Qualidade no percentil {q:.0f} do universo.")
    if g is not None and g >= 65:
        evidence.append(f"Crescimento no percentil {g:.0f}.")
    if v is not None and v >= 65:
        evidence.append(f"Valuation no percentil {v:.0f} (mais atrativo é melhor).")
    if cf is not None and cf >= 65:
        evidence.append(f"Cash flow no percentil {cf:.0f}.")
    if b is not None and b >= 65:
        evidence.append(f"Balanço no percentil {b:.0f}.")
    if rev_yoy is not None and rev_yoy >= 10:
        evidence.append(f"Receita do último trimestre +{rev_yoy:.1f}% YoY.")
    if ni_yoy is not None and ni_yoy >= 10:
        evidence.append(f"Lucro líquido do último trimestre +{ni_yoy:.1f}% YoY.")
    if margin_delta is not None and margin_delta >= 1:
        evidence.append(f"Margem líquida melhorou {margin_delta:.1f} pp YoY.")
    if insider_net is not None and insider_net > 0 and insider_buys > 0:
        evidence.append("Fluxo líquido de insiders open-market positivo nos últimos 30 dias.")

    if zombie:
        risks.append("Cobertura de juros inferior a 1×.")
    if dilution is not None and dilution >= 5:
        risks.append(f"Ações diluídas aumentaram {dilution:.1f}% YoY.")
    if margin_delta is not None and margin_delta <= -2:
        risks.append(f"Margem líquida deteriorou {abs(margin_delta):.1f} pp YoY.")
    if b is not None and b < 35:
        risks.append(f"Balanço apenas no percentil {b:.0f}.")
    if g is not None and g < 30:
        risks.append(f"Crescimento apenas no percentil {g:.0f}.")
    if q is not None and q < 35:
        risks.append(f"Qualidade apenas no percentil {q:.0f}.")
    if insider_net is not None and insider_net < -100_000:
        risks.append("Fluxo líquido de insiders open-market negativo nos últimos 30 dias.")
    capital_labels = {
        "reverse_split_recent": "Reverse split identificado nos últimos 24 meses.",
        "repeated_reverse_splits": "Reverse splits repetidos nos últimos 24 meses.",
        "atm_offering": "Programa ATM / emissão contínua de ações identificado.",
        "equity_financing": "Oferta de capital recente identificada nos filings.",
        "convertible_financing": "Financiamento convertível recente identificado.",
        "variable_price_convertible": "Convertível com preço variável/desconto ao mercado: risco elevado de diluição.",
        "warrants_outstanding": "Warrants associados a financiamento/oferta identificados.",
        "listing_compliance_risk": "Risco de cumprimento das regras de cotação/delisting identificado.",
    }
    for flag in capital_flags:
        label = capital_labels.get(flag)
        if label and label not in risks:
            risks.append(label)

    # Keep the UI concise and deterministic.
    evidence = evidence[:4]
    risks = risks[:4]
    confidence_score = _n(row.get("confidence_score"))
    if confidence_score is not None:
        if confidence_score >= 80 and (len(evidence) >= 2 or risk_gate in ("high", "severe")):
            confidence = "high"
        elif confidence_score >= 60:
            confidence = "medium"
        else:
            confidence = "low"
    elif risk_gate == "severe" or coverage is None or coverage < 40:
        confidence = "low"
    elif risk_gate == "high":
        confidence = "medium"
    elif coverage >= 70 and len(evidence) >= 2:
        confidence = "high"
    else:
        confidence = "medium"

    return {
        "thesis_type": thesis_type,
        "thesis_slug": slug,
        "thesis_confidence": confidence,
        "thesis_summary": summary,
        "thesis_evidence": evidence,
        "thesis_risks": risks,
    }


def _delta(current, previous):
    a, b = _n(current), _n(previous)
    return None if a is None or b is None else a - b


def evolve(row: dict, previous: dict | None = None, previous_date: str | None = None, snapshot_7d: dict | None = None, snapshot_7d_date: str | None = None, snapshot_30d: dict | None = None, snapshot_30d_date: str | None = None) -> dict:
    """Describe direction of the current thesis using quarterly acceleration plus
    the previous persisted daily snapshot when available.

    The result is deliberately rule-based.  'Strengthening' means the measured
    evidence supporting the current thesis improved; it is not a return forecast.
    """
    previous = previous or {}
    snapshot_7d = snapshot_7d or {}
    snapshot_30d = snapshot_30d or {}
    score_delta = _delta(row.get("score"), previous.get("score"))
    quality_delta = _delta(row.get("quality_pct"), previous.get("quality_pct"))
    growth_delta = _delta(row.get("growth_pct"), previous.get("growth_pct"))
    value_delta = _delta(row.get("value_pct"), previous.get("value_pct"))
    insider_net_delta = _delta(row.get("insider_net_value_30d"), previous.get("insider_net_value_30d"))
    analyst_eps_next_y_revision_delta = _delta(row.get("analyst_eps_next_y_revision_30d_pct"), previous.get("analyst_eps_next_y_revision_30d_pct"))
    analyst_eps_next_q_revision_delta = _delta(row.get("analyst_eps_next_q_revision_30d_pct"), previous.get("analyst_eps_next_q_revision_30d_pct"))
    analyst_price_target_upside_delta = _delta(row.get("analyst_price_target_upside_pct"), previous.get("analyst_price_target_upside_pct"))
    latest_earnings_date_changed = bool(previous.get("analyst_latest_earnings_date") and row.get("analyst_latest_earnings_date") and previous.get("analyst_latest_earnings_date") != row.get("analyst_latest_earnings_date"))
    # NOTE: analyst_eps_next_y/q_revision and price_target_upside deltas are
    # returned for the UI but intentionally do not score positive/negative
    # below yet — no weighting has been validated for them. Candidate for a
    # future, deliberate addition rather than an arbitrary threshold now.

    # Multi-horizon persistence context. These are deltas in the underlying
    # daily snapshots, not forecasts. They let the UI distinguish a one-day
    # event from evidence that has persisted for roughly a week/month.
    score_delta_7d = _delta(row.get("score"), snapshot_7d.get("score"))
    score_delta_30d = _delta(row.get("score"), snapshot_30d.get("score"))
    quality_delta_7d = _delta(row.get("quality_pct"), snapshot_7d.get("quality_pct"))
    quality_delta_30d = _delta(row.get("quality_pct"), snapshot_30d.get("quality_pct"))
    growth_delta_7d = _delta(row.get("growth_pct"), snapshot_7d.get("growth_pct"))
    growth_delta_30d = _delta(row.get("growth_pct"), snapshot_30d.get("growth_pct"))
    value_delta_7d = _delta(row.get("value_pct"), snapshot_7d.get("value_pct"))
    value_delta_30d = _delta(row.get("value_pct"), snapshot_30d.get("value_pct"))
    insider_delta_7d = _delta(row.get("insider_net_value_30d"), snapshot_7d.get("insider_net_value_30d"))
    insider_delta_30d = _delta(row.get("insider_net_value_30d"), snapshot_30d.get("insider_net_value_30d"))
    eps_rev_delta_7d = _delta(row.get("analyst_eps_next_y_revision_30d_pct"), snapshot_7d.get("analyst_eps_next_y_revision_30d_pct"))
    eps_rev_delta_30d = _delta(row.get("analyst_eps_next_y_revision_30d_pct"), snapshot_30d.get("analyst_eps_next_y_revision_30d_pct"))
    rev_acc = _n(row.get("revenue_yoy_acceleration_pp"))
    ni_acc = _n(row.get("net_income_yoy_acceleration_pp"))
    margin_delta = _n(row.get("net_margin_yoy_change_pp"))
    dilution = _pct(row.get("diluted_shares_yoy"))
    prior_type = previous.get("thesis_type")
    current_type = row.get("thesis_type")

    positive = 0
    negative = 0
    drivers: list[str] = []

    if score_delta is not None:
        if score_delta >= 3:
            positive += 2; drivers.append(f"Score +{score_delta:.1f} vs última observação.")
        elif score_delta <= -3:
            negative += 2; drivers.append(f"Score {score_delta:.1f} vs última observação.")
    if growth_delta is not None:
        if growth_delta >= 5:
            positive += 1; drivers.append(f"Percentil de crescimento +{growth_delta:.0f}.")
        elif growth_delta <= -5:
            negative += 1; drivers.append(f"Percentil de crescimento {growth_delta:.0f}.")
    if quality_delta is not None:
        if quality_delta >= 5:
            positive += 1; drivers.append(f"Percentil de qualidade +{quality_delta:.0f}.")
        elif quality_delta <= -5:
            negative += 1; drivers.append(f"Percentil de qualidade {quality_delta:.0f}.")
    # Valuation delta is shown as context but deliberately does not score
    # positive/negative: a rising value_pct can mean the stock got cheaper
    # (bullish entry) or that the price fell for a bad reason (bearish) —
    # ambiguous without a price-direction signal, so we surface it without
    # asserting a direction.
    if value_delta is not None and abs(value_delta) >= 8:
        drivers.append(f"Percentil de valuation {value_delta:+.0f} vs última observação.")
    if rev_acc is not None:
        if rev_acc >= 5:
            positive += 2; drivers.append(f"Crescimento de receitas acelerou {rev_acc:+.1f} pp YoY.")
        elif rev_acc <= -5:
            negative += 2; drivers.append(f"Crescimento de receitas desacelerou {rev_acc:.1f} pp YoY.")
    if ni_acc is not None:
        if ni_acc >= 10:
            positive += 1; drivers.append(f"Crescimento do lucro acelerou {ni_acc:+.1f} pp YoY.")
        elif ni_acc <= -10:
            negative += 1; drivers.append(f"Crescimento do lucro desacelerou {ni_acc:.1f} pp YoY.")
    if margin_delta is not None:
        if margin_delta >= 2:
            positive += 1; drivers.append(f"Margem líquida +{margin_delta:.1f} pp YoY.")
        elif margin_delta <= -2:
            negative += 1; drivers.append(f"Margem líquida {margin_delta:.1f} pp YoY.")
    if dilution is not None and dilution >= 8:
        negative += 2; drivers.append(f"Diluição de {dilution:.1f}% YoY.")
    if row.get("zombie") == "yes":
        negative += 2; drivers.append("Cobertura de juros inferior a 1×.")
    if insider_net_delta is not None and abs(insider_net_delta) >= 100_000:
        if insider_net_delta > 0:
            positive += 1; drivers.append("Fluxo líquido de insiders melhorou vs última observação.")
        else:
            negative += 1; drivers.append("Fluxo líquido de insiders piorou vs última observação.")

    changed = bool(prior_type and current_type and prior_type != current_type)
    if changed:
        direction = "changed"
        label = "Mudança de tese"
        summary = f"A classificação mudou de {prior_type} para {current_type}."
    elif positive >= negative + 2:
        direction = "strengthening"
        label = "A reforçar"
        summary = "Os sinais operacionais/quantitativos recentes reforçam a tese atual."
    elif negative >= positive + 2:
        direction = "weakening"
        label = "A enfraquecer"
        summary = "Os sinais recentes deterioraram-se e aumentam o risco de quebra da tese."
    elif previous:
        direction = "stable"
        label = "Estável"
        summary = "Não existe alteração quantitativa suficientemente forte para mudar a direção da tese."
    else:
        direction = "baseline"
        label = "Baseline"
        summary = "Primeira observação persistida; a direção ficará mais robusta à medida que o histórico acumular."

    return {
        "thesis_direction": direction,
        "thesis_direction_label": label,
        "thesis_evolution_summary": summary,
        "thesis_previous_type": prior_type,
        "thesis_previous_date": previous_date,
        "thesis_score_delta": None if score_delta is None else round(score_delta, 2),
        "thesis_quality_delta": None if quality_delta is None else round(quality_delta, 2),
        "thesis_growth_delta": None if growth_delta is None else round(growth_delta, 2),
        "thesis_value_delta": None if value_delta is None else round(value_delta, 2),
        "insider_net_value_delta": None if insider_net_delta is None else round(insider_net_delta, 2),
        "analyst_eps_next_y_revision_delta_pp": None if analyst_eps_next_y_revision_delta is None else round(analyst_eps_next_y_revision_delta, 2),
        "analyst_eps_next_q_revision_delta_pp": None if analyst_eps_next_q_revision_delta is None else round(analyst_eps_next_q_revision_delta, 2),
        "analyst_price_target_upside_delta_pp": None if analyst_price_target_upside_delta is None else round(analyst_price_target_upside_delta, 2),
        "analyst_latest_earnings_date_changed": latest_earnings_date_changed,
        "thesis_history_7d_date": snapshot_7d_date,
        "thesis_history_30d_date": snapshot_30d_date,
        "thesis_score_delta_7d": None if score_delta_7d is None else round(score_delta_7d, 2),
        "thesis_score_delta_30d": None if score_delta_30d is None else round(score_delta_30d, 2),
        "thesis_quality_delta_7d": None if quality_delta_7d is None else round(quality_delta_7d, 2),
        "thesis_quality_delta_30d": None if quality_delta_30d is None else round(quality_delta_30d, 2),
        "thesis_growth_delta_7d": None if growth_delta_7d is None else round(growth_delta_7d, 2),
        "thesis_growth_delta_30d": None if growth_delta_30d is None else round(growth_delta_30d, 2),
        "thesis_value_delta_7d": None if value_delta_7d is None else round(value_delta_7d, 2),
        "thesis_value_delta_30d": None if value_delta_30d is None else round(value_delta_30d, 2),
        "insider_net_value_delta_7d": None if insider_delta_7d is None else round(insider_delta_7d, 2),
        "insider_net_value_delta_30d": None if insider_delta_30d is None else round(insider_delta_30d, 2),
        "analyst_eps_next_y_revision_delta_7d_pp": None if eps_rev_delta_7d is None else round(eps_rev_delta_7d, 2),
        "analyst_eps_next_y_revision_delta_30d_pp": None if eps_rev_delta_30d is None else round(eps_rev_delta_30d, 2),
        "thesis_type_7d_ago": snapshot_7d.get("thesis_type"),
        "thesis_type_30d_ago": snapshot_30d.get("thesis_type"),
        "thesis_evolution_drivers": drivers[:5],
    }
