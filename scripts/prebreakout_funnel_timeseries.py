#!/usr/bin/env python3
"""Aggregate per-slot pre-breakout gate funnels into one time series.

Read-only over data/prebreakout-history; writes data/prebreakout-funnel-timeseries.json.
Purpose: show which gate eliminates candidates over time (share of attempted),
so a filter is only questioned on accumulated evidence, not on a single slot.
"""
import glob, json, os, sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build(history_glob=None):
    pattern = history_glob or os.path.join(ROOT, "data", "prebreakout-history", "*", "*.json")
    rows, total = [], Counter()
    attempted_total = 0
    for path in sorted(glob.glob(pattern)):
        try:
            with open(path, encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            continue
        counts = (d.get("gate_funnel") or {}).get("first_rejection_counts")
        attempted = d.get("attempted")
        if not isinstance(counts, dict) or not isinstance(attempted, int) or attempted <= 0:
            continue
        counts = {k: int(v) for k, v in counts.items() if isinstance(v, int)}
        rows.append({"file": os.path.basename(path), "generated_at": d.get("generated_at"),
                     "attempted": attempted, "first_rejection_counts": counts})
        total.update(counts)
        attempted_total += attempted
    share = {k: round(v / attempted_total, 4) for k, v in total.items()} if attempted_total else {}
    return {"schema": "vestra_prebreakout_funnel_timeseries_v1", "slots": len(rows),
            "attempted_total": attempted_total, "first_rejection_totals": dict(total),
            "first_rejection_share_of_attempted": share,
            "note": "Descriptive only. A high rejection share is not evidence a gate is too strict; "
                    "see prebreakout-paired-gate-audit / negative-controls for forward outcomes.",
            "rows": rows}


def main():
    out = build()
    path = os.path.join(ROOT, "data", "prebreakout-funnel-timeseries.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps({k: out[k] for k in ("slots", "attempted_total", "first_rejection_share_of_attempted")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
