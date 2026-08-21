"""Build a deterministic daily metals brief from the already-fetched metals payload.

No LLM and no external calls here: the report is a transparent narrative layer over
values already present in data/metals.json. That keeps the 06:00 briefing reproducible.
"""
from __future__ import annotations

import datetime as dt


def _inst(payload, ticker):
    for x in payload.get("instruments", []) or []:
        if x.get("ticker") == ticker:
            return x
    return {}


def _signed(v, digits=1, suffix="%"):
    if v is None:
        return "—"
    try:
        x = float(v)
    except Exception:
        return "—"
    return f"{x:+.{digits}f}{suffix}"


def build_metals_brief(payload, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    gold = _inst(payload, "GC=F").get("data", {}) or {}
    silver = _inst(payload, "SI=F").get("data", {}) or {}
    copper = _inst(payload, "HG=F").get("data", {}) or {}
    pressure = payload.get("physical_pressure_index", {}) or {}
    phys = payload.get("physical", {}) or {}
    comex_gold = ((phys.get("comex") or {}).get("gold") or {})
    cot = ((phys.get("positioning") or {}).get("gold") or {})
    deliveries = ((phys.get("deliveries") or {}).get("gold") or {})
    cb = phys.get("central_banks", {}) or {}

    if not gold.get("price"):
        return {"status": "insufficient", "generated_at": now.isoformat(), "title": "Metals Brief", "bullets": []}

    pressure_score = pressure.get("score") if pressure.get("status") == "ok" else None
    trend = gold.get("vs_200d_pct")
    y1 = gold.get("change_1y_pct")
    day = gold.get("day_change_pct")

    if trend is None:
        trend_text = "sem média de 200 dias disponível"
    elif trend >= 8:
        trend_text = f"bem acima da média de 200 dias ({_signed(trend)})"
    elif trend >= 0:
        trend_text = f"acima da média de 200 dias ({_signed(trend)})"
    elif trend <= -8:
        trend_text = f"bem abaixo da média de 200 dias ({_signed(trend)})"
    else:
        trend_text = f"ligeiramente abaixo da média de 200 dias ({_signed(trend)})"

    if pressure_score is None:
        pressure_phrase = "a leitura física ainda não tem cobertura suficiente para um índice agregado"
    elif pressure_score >= 75:
        pressure_phrase = f"a pressão observável é elevada ({pressure_score:.0f}/100)"
    elif pressure_score >= 60:
        pressure_phrase = f"a pressão observável é moderadamente elevada ({pressure_score:.0f}/100)"
    elif pressure_score >= 40:
        pressure_phrase = f"o mercado físico/financeiro está relativamente equilibrado ({pressure_score:.0f}/100)"
    else:
        pressure_phrase = f"a pressão observável é baixa ({pressure_score:.0f}/100)"

    title = "Gold: trend and physical pressure"
    if day is not None and abs(float(day)) >= 1.5:
        title = "Gold moves sharply while the physical picture stays in focus"
    elif pressure_score is not None and pressure_score >= 70:
        title = "Gold physical pressure remains elevated"
    elif trend is not None and abs(float(trend)) <= 5:
        title = "Gold holds near its long-run trend"

    lead = (
        f"O ouro está em {float(gold['price']):,.2f} USD/oz ({_signed(day)} hoje), "
        f"{trend_text}. Em 12 meses acumula {_signed(y1)}; {pressure_phrase}."
    )

    bullets = []
    reg = comex_gold.get("registered_oz")
    if reg:
        bullets.append(f"COMEX registered gold: {float(reg)/1e6:.2f} Moz disponíveis na categoria registered.")
    mm = cot.get("managed_money_net_pct_oi")
    if mm is not None:
        bullets.append(f"CFTC managed money: {_signed(mm)} net do open interest; positioning é financeiro, não stock físico.")
    notices = deliveries.get("daily_notices")
    if notices is not None:
        bullets.append(f"CME delivery notices: {int(notices):,} no dia; notices de clearing não equivalem a retirada do vault.")
    if silver.get("price"):
        bullets.append(f"Prata: {float(silver['price']):,.3f} USD/oz, {_signed(silver.get('day_change_pct'))} hoje e {_signed(silver.get('change_1y_pct'))} em 12 meses.")
    if copper.get("price"):
        bullets.append(f"Cobre: {float(copper['price']):,.3f} USD/lb, {_signed(copper.get('day_change_pct'))} hoje; volatilidade anualizada {copper.get('volatility_annualized_pct','—')}%.")
    if cb.get("status") == "ok" and cb.get("buyers"):
        top = cb["buyers"][0]
        bullets.append(f"Bancos centrais: {top.get('country')} lidera os compradores visíveis no período, com {float(top.get('tonnes',0)):+.1f}t.")

    return {
        "status": "ok",
        "generated_at": now.isoformat(),
        "edition": now.astimezone(dt.timezone.utc).strftime("Daily edition · %d %b %Y"),
        "title": title,
        "lead": lead,
        "bullets": bullets[:6],
        "pressure_score": pressure_score,
        "pressure_label": pressure.get("label"),
        "source_generated_at": payload.get("generated_at"),
    }
