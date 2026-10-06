"""Persistent, explainable zombie-company risk classification.

The classifier is deliberately separate from Vestra Score.  It requires annual
statement persistence before calling a company a probable zombie; one weak year
can never produce that label.
"""
from __future__ import annotations


def _num(value):
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out != out or out in (float("inf"), float("-inf")):
        return None
    return out


def _coverage(row):
    ebit = _num((row or {}).get("ebit"))
    interest = _num((row or {}).get("interest_expense"))
    if interest is None:
        return None
    if interest == 0:
        return float("inf")
    if interest < 0:
        interest = abs(interest)
    return ebit / interest if ebit is not None else None


def classify_zombie_risk(history, *, sector=None, industry=None):
    """Return an explainable structural-risk assessment.

    States:
      not_applicable    financial institutions whose interest expense is operating input
      insufficient_data fewer than two comparable annual observations
      clear             no persistent debt-service stress
      fragile           latest coverage is weak, but persistence is unproven
      candidate         coverage <1 for >=2 consecutive observed years
      probable          coverage <1 for >=3 consecutive years plus financing dependence
    """
    sec = str(sector or "").lower()
    ind = str(industry or "").lower()
    if "financial" in sec and any(k in ind for k in ("bank", "credit", "savings", "thrift", "insurance", "insur")):
        return {
            "state": "not_applicable", "years_below_one": 0,
            "reason": "Modelo não aplicável a bancos/seguradoras; juros fazem parte da operação.",
            "support": [], "latest_interest_coverage": None,
        }

    rows = [r for r in (history or []) if isinstance(r, dict)]
    observed = [(r, _coverage(r)) for r in rows]
    observed = [(r, c) for r, c in observed if c is not None]
    if len(observed) < 2:
        return {
            "state": "insufficient_data", "years_below_one": 0,
            "reason": "Histórico anual insuficiente para testar persistência.",
            "support": [], "latest_interest_coverage": observed[0][1] if observed else None,
        }

    latest = observed[0][1]
    below = 0
    for _, cov in observed:
        if cov < 1.0:
            below += 1
        else:
            break

    support = []
    recent = [r for r, _ in observed[:3]]
    latest_row = observed[0][0]
    debt = _num(latest_row.get("total_debt"))
    cash = _num(latest_row.get("total_cash"))
    if debt is not None and cash is not None and debt > cash:
        support.append("dívida líquida positiva")

    fcf_vals = [_num(r.get("free_cash_flow")) for r in recent]
    fcf_neg = sum(v is not None and v < 0 for v in fcf_vals)
    if fcf_neg >= 2:
        support.append("FCF negativo em pelo menos 2 dos últimos 3 exercícios")

    debt_vals = [_num(r.get("total_debt")) for r in recent]
    debt_obs = [v for v in debt_vals if v is not None]
    if len(debt_obs) >= 2 and debt_obs[0] >= debt_obs[-1] * 1.05:
        support.append("dívida não está a desalavancar")

    if below >= 3 and support:
        state = "probable"
        reason = f"EBIT não cobre juros há {below} exercícios consecutivos; " + "; ".join(support) + "."
    elif below >= 2:
        state = "candidate"
        reason = f"EBIT não cobre juros há {below} exercícios consecutivos; persistência confirmada, mas dependência financeira ainda não é suficiente para classificação provável."
    elif latest < 1.5:
        state = "fragile"
        reason = f"Cobertura de juros recente fraca ({latest:.2f}×), sem persistência plurianual suficiente."
    else:
        state = "clear"
        reason = f"Sem padrão zombie persistente; cobertura de juros recente {latest:.2f}×."

    return {
        "state": state,
        "years_below_one": below,
        "reason": reason,
        "support": support,
        "latest_interest_coverage": latest,
    }


__all__ = ["classify_zombie_risk"]
