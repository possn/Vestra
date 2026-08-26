from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path

from peer_benchmark import clean_values, percentile_rank

ROOT = Path(__file__).resolve().parents[1]
STOCKS = ROOT / "data" / "stocks.json"
OUT = ROOT / "data" / "score_benchmark_audit.json"
MIN_PEERS = 20

MODEL_FIELDS = {
    "bank": ["roe", "roa", "profit_margin", "efficiency_ratio_proxy", "provision_to_revenue", "equity_to_assets", "revenue_growth", "earnings_growth", "net_interest_income_yoy", "price_to_book", "trailing_pe", "forward_pe", "dividend_yield", "beta"],
    "reit": ["reit_ffo_per_share_proxy", "roe", "profit_margin", "reit_net_debt_to_ebitda", "revenue_growth", "earnings_growth", "reit_p_ffo_proxy", "price_to_book", "dividend_yield", "reit_ffo_payout_proxy", "beta"],
    "insurance": ["roe", "roa", "profit_margin", "insurance_claims_to_revenue", "insurance_operating_ratio_proxy", "insurance_equity_to_assets", "debt_to_equity", "revenue_growth", "earnings_growth", "price_to_book", "trailing_pe", "dividend_yield", "beta"],
    "utility": ["roe", "operating_margin", "roce_proxy", "debt_to_equity", "dividend_yield", "payout_ratio", "forward_pe", "trailing_pe", "price_to_book", "revenue_growth", "earnings_growth", "beta"],
    "energy": ["roe", "operating_margin", "roce_proxy", "debt_to_equity", "trailing_pe", "forward_pe", "enterprise_to_ebitda", "revenue_growth", "earnings_growth", "beta"],
    "biotech": ["gross_margin", "operating_margin", "revenue_growth", "earnings_growth", "debt_to_equity", "current_ratio", "quick_ratio", "beta"],
    "growth_tech": ["roe", "roa", "gross_margin", "operating_margin", "revenue_growth", "earnings_growth", "debt_to_equity", "forward_pe", "enterprise_to_ebitda", "peg_ratio", "beta"],
}


def finite(value):
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def median(values):
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    mid = len(vals) // 2
    return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2.0


def main():
    payload = json.loads(STOCKS.read_text(encoding="utf-8"))
    rows = [x for x in (payload.get("stocks") or []) if isinstance(x, dict)]
    equities = [x for x in rows if str(x.get("quote_type") or "").upper() not in {"ETF", "CRYPTO", "FUND", "MUTUALFUND"}]
    result = {}

    for model, fields in MODEL_FIELDS.items():
        peers = [x for x in equities if str(x.get("score_model") or "") == model]
        metrics = []
        eligible = 0
        for field in fields:
            peer_values = clean_values(x.get(field) for x in peers)
            global_values = clean_values(x.get(field) for x in equities)
            is_eligible = len(peer_values) >= MIN_PEERS
            eligible += int(is_eligible)
            shifts = []
            for row in peers:
                value = finite(row.get(field))
                if value is None:
                    continue
                peer_pct = percentile_rank(value, peer_values)
                global_pct = percentile_rank(value, global_values)
                if peer_pct is not None and global_pct is not None:
                    shifts.append(abs(peer_pct - global_pct))
            metrics.append({
                "field": field,
                "peer_observations": len(peer_values),
                "global_observations": len(global_values),
                "peer_first_eligible": is_eligible,
                "median_absolute_percentile_shift": round(median(shifts), 3) if shifts else None,
                "max_absolute_percentile_shift": round(max(shifts), 3) if shifts else None,
            })
        result[model] = {
            "peer_rows": len(peers),
            "metrics_defined": len(fields),
            "metrics_peer_first_eligible": eligible,
            "eligible_ratio": round(eligible / len(fields), 3) if fields else None,
            "metrics": metrics,
        }

    OUT.write_text(json.dumps({
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "production_unchanged": True,
        "min_peer_observations": MIN_PEERS,
        "models": result,
    }, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
