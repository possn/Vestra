"""Independent, explainable Zombie Risk classifier.

This is a structural diagnostic, not a score component. It deliberately does
not modify Vestra Score, Conviction or the canonical Risk Gate. Missing annual
statement evidence remains unavailable rather than being imputed.
"""
from __future__ import annotations

import logging

log = logging.getLogger("zombie_risk")
MODEL_VERSION = "1.0"


def _num(value):
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out != out or out in (float("inf"), float("-inf")):
        return None
    return out


def _excluded(model):
    q = str(getattr(model, "quote_type", "") or "").upper()
    if q in {"ETF", "MUTUALFUND", "FUND", "CRYPTO"}:
        return True
    sector = str(getattr(model, "sector", "") or "").lower()
    industry = str(getattr(model, "industry", "") or "").lower()
    return "financial" in sector and any(k in industry for k in ("bank", "credit", "savings", "thrift", "insurance", "insur"))


def _set(model, status, label, evidence, weak, latest, reasons):
    model.zombie_risk_status = status
    model.zombie_risk_label = label
    model.zombie_risk_evidence_years = evidence
    model.zombie_risk_weak_years = weak
    model.zombie_risk_latest_interest_coverage = latest
    model.zombie_risk_reasons = reasons
    model.zombie_risk_model_version = MODEL_VERSION


def assess(model):
    if _excluded(model):
        _set(model, "not_applicable", "Modelo não aplicável", 0, 0, None, ["Setor/instrumento requer modelo próprio"])
        return model

    history = getattr(model, "annual_zombie_history", None)
    rows = [row for row in (history or []) if isinstance(row, dict)]
    coverage_rows = []
    for row in rows:
        coverage = _num(row.get("interest_coverage"))
        interest = _num(row.get("interest_expense"))
        if coverage is None or interest is None or interest <= 0:
            continue
        coverage_rows.append((row, coverage))

    debt = _num(getattr(model, "total_debt", None))
    if debt is not None and debt <= 0:
        _set(model, "clear", "Sem risco zombie", len(coverage_rows), 0, None, ["Sem dívida financeira observada"])
        return model

    if len(coverage_rows) < 2:
        _set(model, "unavailable", "Dados insuficientes", len(coverage_rows), 0, coverage_rows[0][1] if coverage_rows else None, ["São necessários pelo menos 2 exercícios com EBIT e juros observados"])
        return model

    latest = coverage_rows[0][1]
    weak_flags = [coverage < 1.0 for _, coverage in coverage_rows]
    consecutive_weak = 0
    for weak in weak_flags:
        if not weak:
            break
        consecutive_weak += 1
    weak_count = sum(weak_flags)
    latest_row = coverage_rows[0][0]
    latest_fcf = _num(latest_row.get("free_cash_flow"))
    latest_debt = _num(latest_row.get("total_debt"))
    latest_cash = _num(latest_row.get("total_cash"))
    net_debt_positive = latest_debt is not None and latest_cash is not None and latest_debt - latest_cash > 0
    reasons = []

    if consecutive_weak >= 3:
        reasons.append(f"EBIT não cobre juros há {consecutive_weak} exercícios consecutivos")
        support = False
        if latest_fcf is not None and latest_fcf < 0:
            reasons.append("Free cash flow anual mais recente é negativo")
            support = True
        if net_debt_positive:
            reasons.append("Dívida líquida observada é positiva")
            support = True
        if support:
            _set(model, "probable", "Zombie provável", len(coverage_rows), weak_count, latest, reasons)
        else:
            reasons.append("Sem segundo sinal de stress suficiente para confirmação")
            _set(model, "candidate", "Candidato a zombie", len(coverage_rows), weak_count, latest, reasons)
        return model

    if consecutive_weak >= 2:
        reasons.append("EBIT não cobre juros em 2 exercícios consecutivos")
        if latest_fcf is not None and latest_fcf < 0:
            reasons.append("Free cash flow anual mais recente é negativo")
        _set(model, "candidate", "Candidato a zombie", len(coverage_rows), weak_count, latest, reasons)
        return model

    if latest < 1.0 or weak_count >= 2:
        reasons.append("Cobertura de juros frágil, mas sem persistência suficiente")
        _set(model, "fragile", "Fragilidade financeira", len(coverage_rows), weak_count, latest, reasons)
        return model

    _set(model, "clear", "Sem risco zombie", len(coverage_rows), weak_count, latest, ["Cobertura de juros não mostra padrão persistente abaixo de 1×"])
    return model


def enrich(raw):
    counts = {}
    for model in raw or []:
        assess(model)
        status = getattr(model, "zombie_risk_status", "unavailable")
        counts[status] = counts.get(status, 0) + 1
    log.info("Zombie risk: %s", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    return raw


__all__ = ["assess", "enrich", "MODEL_VERSION"]
