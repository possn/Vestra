"""Historical 165-company Biotech de-duplication candidate diagnostic.
Non-publishing: reads canonical data, never changes scores, gates or output data.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import score_audit
import score_peer_shadow


class BiotechHistoricalCandidate(unittest.TestCase):
    def test_gross_margin_only_operating_quality_candidate(self):
        payload = json.loads((ROOT / "data" / "stocks.json").read_text(encoding="utf-8"))
        equities, shadow, _ = score_peer_shadow.build_shadow(payload.get("stocks") or [])
        peers = [r for r in equities if r.get("score_model") == "biotech"]
        native = {r["ticker"]: r for r in shadow if r.get("score_model") == "biotech"}
        self.assertGreaterEqual(len(peers), 100, "Historical biotech cohort unexpectedly shrunk")
        pairs = []
        rankings = []
        parity = []
        for row in peers:
            original = native.get(row["ticker"])
            if not original:
                continue
            dims = original.get("shadow_dimensions") or {}
            old_quality = score_peer_shadow.n(dims.get("Operating Quality"))
            runway = score_peer_shadow.n(dims.get("Cash Runway"))
            gross = score_peer_shadow.ShadowContext(row, peers, equities).p("gross_margin")
            raw = score_peer_shadow.raw_score(row)
            if old_quality is None or gross is None or raw is None:
                continue
            parity.append(abs(score_peer_shadow.n((row.get("score_dimensions") or {}).get("Operating Quality")) - old_quality))
            rankings.append((row["ticker"], raw, raw + .10 * (gross - old_quality)))
            if runway is not None:
                pairs.append((runway, gross))
        def ranks(values):
            return {ticker: i for i, (ticker, _) in enumerate(sorted(values, key=lambda t: (-t[1], t[0])), 1)}
        original_ranks = ranks([(t, before) for t, before, _ in rankings])
        candidate_ranks = ranks([(t, after) for t, _, after in rankings])
        shifts = [abs(original_ranks[t] - candidate_ranks[t]) for t in original_ranks]
        outcome = {
            "cohort_rows": len(peers),
            "comparable_rows": len(pairs),
            "native_quality_max_shadow_delta": max(parity) if parity else None,
            "gross_margin_only_runway_spearman": round(score_audit.spearman_pairs(pairs), 4) if len(pairs) >= 20 else None,
            "ranking_rows": len(rankings),
            "rank_shift_ge_10": sum(x >= 10 for x in shifts),
            "max_rank_shift": max(shifts) if shifts else None,
            "mean_rank_shift": round(sum(shifts) / len(shifts), 2) if shifts else None,
            "candidate_in_production": False,
        }
        print("BIOTECH_HISTORICAL_CANDIDATE " + json.dumps(outcome, sort_keys=True), flush=True)
        self.assertGreaterEqual(len(pairs), 100)
        self.assertIsNotNone(outcome["gross_margin_only_runway_spearman"])


if __name__ == "__main__":
    unittest.main()
