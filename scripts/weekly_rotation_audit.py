from __future__ import annotations

import json
import math
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STARTUP = ROOT / "data" / "stocks-startup.json"
OUTPUT = ROOT / "data" / "weekly-rotation-audit.json"

THEMES = [
    ("Semicondutores", re.compile(r"semiconductor|semiconductors|chip|foundry|wafer|integrated circuit", re.I)),
    ("Biotecnologia", re.compile(r"biotech|biotechnology|genomic|genomics|gene therap|life sciences", re.I)),
    ("Minerais & metais", re.compile(r"metal|mining|miner|copper|lithium|uranium|gold|silver|steel|aluminum|aluminium|rare earth", re.I)),
    ("Agricultura", re.compile(r"agricultur|agribusiness|farm|crop|seed|fertili[sz]er|grain|potash", re.I)),
    ("Energia", re.compile(r"energy|oil|gas|petroleum|exploration|drilling|refin", re.I)),
    ("Defesa & aeroespacial", re.compile(r"defen[cs]e|aerospace|military|weapon|missile", re.I)),
    ("IA & software", re.compile(r"artificial intelligence|machine learning|software|cloud|saas|cyber|data infrastructure", re.I)),
    ("Bancos", re.compile(r"bank|banks|banking|financial services", re.I)),
    ("Imobiliário", re.compile(r"real estate|reit|property", re.I)),
    ("Consumo discricionário", re.compile(r"consumer cyclical|consumer discretionary|auto manufacturer|travel|leisure|retail", re.I)),
]

FUND_NAME = re.compile(r"\bETF\b|ISHARES|VANGUARD|XTRACKERS|SPDR|LYXOR|AMUNDI|WISDOMTREE|INVESCO")


def unpack(payload: dict) -> dict:
    if payload.get("layout") != "field_rows_v1":
        return payload
    fields = payload.get("fields") or []
    rows = payload.get("rows") or []
    stocks = []
    for values in rows:
        if not isinstance(values, list):
            continue
        stocks.append({field: values[i] for i, field in enumerate(fields[: len(values)])})
    meta = {k: v for k, v in payload.items() if k not in {"layout", "fields", "rows"}}
    return {**meta, "stocks": stocks}


def number(value):
    if value is None or value == "":
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def is_fund(stock: dict) -> bool:
    quote_type = str(stock.get("quote_type") or "").strip().upper()
    name = str(stock.get("name") or "").strip().upper()
    return quote_type in {"ETF", "MUTUALFUND", "FUND"} or bool(FUND_NAME.search(name))


def weekly_return(stock: dict):
    market = number(stock.get("market_return_5d_pct"))
    if market is not None:
        return market
    return number(stock.get("opportunity_return_5d_pct"))


def median(values):
    xs = [x for x in values if x is not None and math.isfinite(x)]
    return statistics.median(xs) if xs else None


def build_audit(payload: dict) -> dict:
    decoded = unpack(payload)
    stocks = [
        s for s in (decoded.get("stocks") or [])
        if isinstance(s, dict)
        and not is_fund(s)
        and str(s.get("zombie") or "").strip().lower() != "yes"
    ]

    rows = []
    for label, pattern in THEMES:
        members = [
            s for s in stocks
            if pattern.search(
                f"{s.get('sector') or ''} {s.get('industry') or ''} {s.get('name') or ''}"
            )
        ]
        weekly = [s for s in members if weekly_return(s) is not None]
        r5 = [weekly_return(s) for s in weekly]
        r20 = [
            number(s.get("market_return_20d_pct"))
            if number(s.get("market_return_20d_pct")) is not None
            else number(s.get("opportunity_return_20d_pct"))
            for s in weekly
        ]
        med5 = median(r5)
        med20 = median(r20)
        breadth = (sum(1 for x in r5 if x > 0) / len(r5) * 100.0) if r5 else None
        ready = len(weekly) >= 4
        rank = None
        signal = "A formar série"
        if ready:
            rank = (med5 or 0.0) * 1.4 + ((breadth or 0.0) - 50.0) * 0.08 + (med20 or 0.0) * 0.25
            if med5 >= 2 and breadth >= 60:
                signal = "Entrada forte"
            elif med5 >= 0.5 and breadth >= 55:
                signal = "A receber capital"
            elif med5 <= -2 and breadth <= 40:
                signal = "Saída forte"
            elif med5 <= -0.5 and breadth <= 45:
                signal = "A perder capital"
            elif med5 > 0:
                signal = "A melhorar"
            elif med5 < 0:
                signal = "A enfraquecer"
            else:
                signal = "Rotação mista"
        rows.append({
            "label": label,
            "members": len(members),
            "weekly": len(weekly),
            "ready": ready,
            "median_5d_pct": None if med5 is None else round(med5, 4),
            "breadth_pct": None if breadth is None else round(breadth, 2),
            "median_20d_pct": None if med20 is None else round(med20, 4),
            "rank": None if rank is None else round(rank, 4),
            "signal": signal,
        })

    ready_rows = sorted((r for r in rows if r["ready"]), key=lambda r: r["rank"], reverse=True)
    inflows = [r for r in ready_rows if r["median_5d_pct"] > 0 and r["breadth_pct"] >= 50][:3]
    relative = []
    if not inflows and ready_rows:
        med_rank = statistics.median(r["rank"] for r in ready_rows)
        relative = [r for r in ready_rows if r["rank"] > med_rank][:3]
    relative_labels = {r["label"] for r in relative}
    outflows = sorted(
        (
            r for r in ready_rows
            if r["median_5d_pct"] < 0
            and r["breadth_pct"] <= 50
            and r["label"] not in relative_labels
        ),
        key=lambda r: r["rank"],
    )[:3]

    return {
        "schema_version": 1,
        "generated_at": decoded.get("generated_at"),
        "coverage": {
            "ready": sum(1 for r in rows if r["ready"]),
            "total": len(rows),
            "pending": [r["label"] for r in rows if not r["ready"]],
            "stocks_with_market_return_5d": sum(1 for s in stocks if number(s.get("market_return_5d_pct")) is not None),
            "eligible_stocks": len(stocks),
        },
        "groups": {
            "inflows": [r["label"] for r in inflows],
            "relative_destinations": [r["label"] for r in relative],
            "outflows": [r["label"] for r in outflows],
        },
        "themes": rows,
    }


def main() -> None:
    payload = json.loads(STARTUP.read_text(encoding="utf-8"))
    audit = build_audit(payload)
    OUTPUT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    c = audit["coverage"]
    print(f"weekly rotation coverage: {c['ready']}/{c['total']} themes; "
          f"{c['stocks_with_market_return_5d']}/{c['eligible_stocks']} equities with market 5d return")


if __name__ == "__main__":
    main()
