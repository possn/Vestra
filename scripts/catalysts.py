"""Catalyst & Risk Engine for Vestra v4.8.

Builds a small, auditable event timeline from facts already collected by the
pipeline. It never invents a date: undated signals are labelled as recent
windows instead of being presented as calendar events.
"""
from __future__ import annotations

import datetime as dt


def _num(v):
    try:
        if v is None or isinstance(v, bool):
            return None
        return float(v)
    except Exception:
        return None


def _date(v):
    if not v:
        return None
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except Exception:
        return None


def _event(kind, label, *, date=None, window=None, tone="neutral", importance="medium", source=None, evidence=None):
    return {
        "kind": kind,
        "label": label,
        "date": str(date) if date else None,
        "window": window,
        "tone": tone,
        "importance": importance,
        "source": source,
        "evidence": evidence,
    }


def assess(row: dict) -> dict:
    today = dt.date.today()
    events = []

    earnings = _date(row.get("analyst_next_earnings_date"))
    if earnings:
        days = (earnings - today).days
        if days >= -1:
            importance = "high" if 0 <= days <= 14 else "medium"
            events.append(_event(
                "earnings",
                "Resultados trimestrais",
                date=earnings,
                tone="event",
                importance=importance,
                source="analyst/calendar",
                evidence=f"{days} dias" if days >= 0 else "data recente",
            ))

    signal = str(row.get("estimate_signal") or "").lower()
    ems = _num(row.get("estimate_momentum_score"))
    if signal == "improving":
        events.append(_event(
            "estimates", "Expectativas dos analistas a melhorar",
            window="30d", tone="positive", importance="medium",
            source="analyst estimates", evidence=f"Momentum {ems:.0f}/100" if ems is not None else None,
        ))
    elif signal == "deteriorating":
        events.append(_event(
            "estimates", "Expectativas dos analistas a deteriorar",
            window="30d", tone="risk", importance="high",
            source="analyst estimates", evidence=f"Momentum {ems:.0f}/100" if ems is not None else None,
        ))

    buys = int(_num(row.get("insider_buy_count_30d")) or 0)
    sells = int(_num(row.get("insider_sell_count_30d")) or 0)
    if buys > 0:
        events.append(_event(
            "insiders", f"{buys} compra{'s' if buys != 1 else ''} de insiders",
            window="30d", tone="positive", importance="medium",
            source="SEC Form 4", evidence=f"{sells} vendas no mesmo período" if sells else "sem vendas registadas no período",
        ))
    elif sells >= 3:
        events.append(_event(
            "insiders", f"{sells} vendas de insiders",
            window="30d", tone="risk", importance="medium",
            source="SEC Form 4",
        ))

    thesis = str(row.get("thesis_direction") or "").lower()
    delta7 = _num(row.get("thesis_score_delta_7d"))
    if thesis == "up":
        events.append(_event(
            "thesis", "Tese quantitativa a melhorar", window="7–30d",
            tone="positive", importance="medium", source="Vestra history",
            evidence=f"Score 7d {delta7:+.1f}" if delta7 is not None else None,
        ))
    elif thesis == "down":
        events.append(_event(
            "thesis", "Tese quantitativa a piorar", window="7–30d",
            tone="risk", importance="high", source="Vestra history",
            evidence=f"Score 7d {delta7:+.1f}" if delta7 is not None else None,
        ))

    flags = list(row.get("capital_structure_flags") or [])
    cap_risk = str(row.get("capital_structure_risk") or row.get("risk_gate") or "").lower()
    if flags:
        labels = {
            "atm_offering": "ATM / emissão contínua de ações",
            "convertible_financing": "Financiamento convertível",
            "variable_price_convertible": "Convertível com preço variável",
            "warrants_outstanding": "Warrants / potencial diluição",
            "listing_compliance_risk": "Risco de compliance / delisting",
            "equity_financing": "Oferta / financiamento por capital",
            "reverse_split_recent": "Reverse split recente",
            "repeated_reverse_splits": "Reverse splits repetidos",
        }
        severe = cap_risk in {"high", "severe"} or "variable_price_convertible" in flags
        recent_reverse = _date(row.get("reverse_split_latest_date"))
        top = [labels.get(x, x.replace("_", " ")) for x in flags[:3]]
        events.append(_event(
            "capital_structure",
            "Estrutura de capital: " + " · ".join(top),
            date=recent_reverse,
            window=None if recent_reverse else "filings recentes",
            tone="risk",
            importance="high" if severe else "medium",
            source="SEC filings",
            evidence=f"Risk {cap_risk or 'watch'}",
        ))

    congress = row.get("congress_trades") or []
    if isinstance(congress, list) and congress:
        events.append(_event(
            "congress", f"{len(congress)} operação{'ões' if len(congress) != 1 else ''} declarada{'s' if len(congress) != 1 else ''} no Congresso",
            window="recente", tone="neutral", importance="low", source="STOCK Act / Bargo",
        ))

    rank = {"high": 0, "medium": 1, "low": 2}
    tone_rank = {"risk": 0, "event": 1, "positive": 2, "neutral": 3}
    events.sort(key=lambda e: (
        0 if e.get("date") and _date(e.get("date")) and _date(e.get("date")) >= today else 1,
        _date(e.get("date")) or dt.date.max,
        rank.get(e.get("importance"), 9),
        tone_rank.get(e.get("tone"), 9),
    ))

    future_dates = [_date(e.get("date")) for e in events]
    future_dates = [d for d in future_dates if d and d >= today]
    risk_count = sum(1 for e in events if e.get("tone") == "risk")
    positive_count = sum(1 for e in events if e.get("tone") == "positive")
    high_count = sum(1 for e in events if e.get("importance") == "high")

    if risk_count and high_count:
        summary = "Catalisadores com risco material próximo"
    elif future_dates:
        summary = "Há eventos datados a acompanhar"
    elif positive_count:
        summary = "Momentum recente favorável, sem evento datado dominante"
    elif events:
        summary = "Sinais recentes a acompanhar"
    else:
        summary = "Sem catalisador material identificado nos dados atuais"

    return {
        "catalyst_events": events[:8],
        "catalyst_next_date": str(min(future_dates)) if future_dates else None,
        "catalyst_risk_count": risk_count,
        "catalyst_positive_count": positive_count,
        "catalyst_summary": summary,
    }
