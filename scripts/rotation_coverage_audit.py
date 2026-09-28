from __future__ import annotations

import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "data" / "stocks-index.json"
OUT = ROOT / "data" / "rotation_coverage_audit.json"

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


def number(value):
    if value in (None, ""):
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def median(values):
    xs = sorted(x for x in values if x is not None and math.isfinite(x))
    if not xs:
        return None
    mid = len(xs) // 2
    return xs[mid] if len(xs) % 2 else (xs[mid - 1] + xs[mid]) / 2


def weekly_return(row):
    return number(row.get("market_return_5d_pct")) if number(row.get("market_return_5d_pct")) is not None else number(row.get("opportunity_return_5d_pct"))


def main():
    payload = json.loads(INDEX.read_text(encoding="utf-8"))
    stocks = payload.get("stocks") or []
    rows = []
    for label, pattern in THEMES:
        members = []
        for stock in stocks:
            quote_type = str(stock.get("quote_type") or "").upper()
            if quote_type in {"ETF", "MUTUALFUND"} or str(stock.get("zombie") or "").lower() == "yes":
                continue
            haystack = " ".join(str(stock.get(k) or "") for k in ("sector", "industry", "name"))
            if pattern.search(haystack):
                members.append(stock)
        weekly = [(stock, weekly_return(stock)) for stock in members]
        weekly = [(stock, value) for stock, value in weekly if value is not None]
        values = [value for _, value in weekly]
        med5 = median(values)
        breadth = (sum(1 for value in values if value > 0) / len(values) * 100.0) if values else None
        rows.append({
            "label": label,
            "members": len(members),
            "weekly": len(weekly),
            "ready": len(weekly) >= 4,
            "median_5d_pct": round(med5, 4) if med5 is not None else None,
            "breadth_pct": round(breadth, 2) if breadth is not None else None,
        })

    result = {
        "schema_version": 1,
        "source_generated_at": payload.get("generated_at"),
        "total_themes": len(rows),
        "ready_themes": sum(1 for row in rows if row["ready"]),
        "rows": rows,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"weekly rotation coverage: {result['ready_themes']}/{result['total_themes']} themes ready")
    for row in rows:
        state = "ready" if row["ready"] else "pending"
        print(f"- {row['label']}: {row['weekly']}/{row['members']} weekly ({state}); median5={row['median_5d_pct']} breadth={row['breadth_pct']}")


if __name__ == "__main__":
    main()
