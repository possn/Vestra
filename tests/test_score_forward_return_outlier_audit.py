import json
import math
import unittest
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "data" / "score_validation_history.json"
COMMON_SPLIT_FACTORS = (2, 3, 4, 5, 10, 20, 25, 50, 100)


def finite(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def split_like_ratio(ratio, tolerance=0.03):
    if ratio is None or ratio <= 0:
        return None
    candidates = list(COMMON_SPLIT_FACTORS) + [1.0 / x for x in COMMON_SPLIT_FACTORS]
    best = min(candidates, key=lambda x: abs(ratio / x - 1.0))
    return best if abs(ratio / best - 1.0) <= tolerance else None


class ScoreForwardReturnOutlierAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        payload = json.loads(HISTORY.read_text(encoding="utf-8"))
        cls.outcomes = [
            row for row in (payload.get("outcomes") or [])
            if isinstance(row, dict) and int(row.get("horizon_days") or 0) == 28
        ]

    def test_audit_realised_return_outliers_and_split_like_ratios(self):
        self.assertGreater(len(self.outcomes), 100)

        ranked = sorted(
            self.outcomes,
            key=lambda row: abs(finite(row.get("return_pct")) or 0.0),
            reverse=True,
        )
        print("forward-validation 28d largest absolute returns:")
        suspicious = []
        ticker_counts = Counter()
        ticker_patterns = defaultdict(list)

        for row in ranked[:60]:
            p0 = finite(row.get("start_price"))
            p1 = finite(row.get("end_price"))
            ret = finite(row.get("return_pct"))
            ratio = (p1 / p0) if p0 and p1 is not None else None
            split_factor = split_like_ratio(ratio)
            ticker = str(row.get("ticker") or "")
            if ret is not None and abs(ret) >= 80:
                ticker_counts[ticker] += 1
            if split_factor is not None:
                ticker_patterns[ticker].append(split_factor)
                suspicious.append((ticker, row.get("cohort_date"), ratio, split_factor, ret))
            print(
                f"  {ticker:12s} cohort={row.get('cohort_date')} "
                f"model={row.get('score_model')} start={p0} end={p1} "
                f"ratio={ratio:.6f} return={ret:.2f}% "
                f"split_like={split_factor}"
                if ratio is not None and ret is not None
                else f"  {ticker:12s} incomplete outcome"
            )

        print("tickers with repeated >=80% absolute 28d returns:", ticker_counts.most_common(20))
        print("split-like outcomes:", suspicious[:40])
        print("split-like factors by ticker:", dict(sorted(ticker_patterns.items())))

        # Diagnostic contract: do not silently drop or mutate existing outcomes.
        # The audit is intentionally observational; remediation must be explicit.
        before = len(self.outcomes)
        after = len([row for row in self.outcomes if finite(row.get("return_pct")) is not None])
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main(verbosity=2)
