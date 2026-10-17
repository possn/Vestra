"""Measure candidate Biotech redundancy on the exact published 165-name peer-shadow cohort.

Audit only: never changes the published score, its components or the threshold.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import score_audit
import score_peer_shadow


class PublishedBiotechCandidateAudit(unittest.TestCase):
    def test_report_peer_first_candidates_without_publishing(self):
        payload = json.loads((ROOT / "data/stocks.json").read_text())
        stocks = payload.get("stocks") or []
        _, published_shadow, _ = score_peer_shadow.build_shadow(stocks)
        benchmark_rows = [r for r in published_shadow if r.get("score_model") == "biotech"]
        self.assertGreaterEqual(len(benchmark_rows), 20)
        # Use the exact same model universe and production-equivalent rank
        # implementation as the existing architecture regression check.
        equities = [r for r in stocks if isinstance(r, dict)
                    and str(r.get("quote_type") or "").upper() not in {"ETF","CRYPTO","FUND","MUTUALFUND"}
                    and str(r.get("pipeline_status") or "") not in {"equity_catalog_only","equity_carried_forward"}
                    and score_peer_shadow.raw_score(r) is not None]
        peers = [r for r in equities if r.get("score_model") == "biotech"]
        by_ticker = {str(r.get("ticker")): r for r in peers}
        results = []
        for roa_weight in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5):
            points = []
            rank_inputs = []
            for native in benchmark_rows:
                row = by_ticker.get(str(native.get("ticker")))
                if row is None:
                    continue
                ctx = score_peer_shadow.ShadowContext(row, peers, equities)
                gross, roa = ctx.p("gross_margin"), ctx.p("roa")
                available = [(x, w) for x, w in ((gross, 1 - roa_weight), (roa, roa_weight))
                             if x is not None and w > 0]
                quality = (sum(v * w for v, w in available) / sum(w for _, w in available)) if available else None
                dimensions = native.get("shadow_dimensions") or {}
                runway = score_peer_shadow.n(dimensions.get("Cash Runway"))
                baseline_quality = score_peer_shadow.n(dimensions.get("Operating Quality"))
                raw = score_peer_shadow.n(native.get("production_score_raw"))
                if runway is not None and quality is not None:
                    points.append((runway, quality))
                if raw is not None and quality is not None and baseline_quality is not None:
                    rank_inputs.append((native.get("ticker"),raw,raw + (quality-baseline_quality)*0.1))
            rho = score_audit.spearman_pairs(points)
            def ranked(index):
                return {ticker: n for n, (ticker, *_) in enumerate(sorted(rank_inputs,key=lambda r:(-r[index],r[0])),1)}
            first, second = ranked(1), ranked(2)
            shifts = [abs(first[k]-second[k]) for k in first]
            results.append({"roa_weight":roa_weight,"pairs":len(points),"rho":round(rho,4) if rho is not None else None,
                            "rank_rows":len(rank_inputs),"max_shift":max(shifts) if shifts else None,
                            "shift_ge_10":sum(d >= 10 for d in shifts)})
        print("BIOTECH_PUBLISHED_HISTORICAL_SWEEP "+json.dumps({"historical_rows":len(benchmark_rows),"results":results},sort_keys=True))
        self.assertEqual(len(results),6)
        self.assertGreaterEqual(min(x["rank_rows"] for x in results),20)


if __name__ == "__main__":
    unittest.main()
