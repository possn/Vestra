import unittest

from scripts.build_market_shards import apply_market_identity_fallback


class MarketIdentityFallbackTests(unittest.TestCase):
    def test_restores_missing_sector_and_industry_from_known_identity(self):
        current = {"ticker": "GS", "sector": None, "industry": None, "score": 70}
        fallback = {
            "sector": "Financial Services",
            "industry": "Capital Markets",
            "quote_type": "EQUITY",
        }
        out = apply_market_identity_fallback(current, fallback)
        self.assertEqual(out["sector"], "Financial Services")
        self.assertEqual(out["industry"], "Capital Markets")
        self.assertEqual(out["score"], 70)
        self.assertNotIn("quote_type", out)

    def test_keeps_current_sector_and_only_backfills_missing_industry(self):
        current = {"ticker": "FTI", "sector": "Energy", "industry": ""}
        fallback = {
            "sector": "Industrials",
            "industry": "Oil & Gas Equipment & Services",
        }
        out = apply_market_identity_fallback(current, fallback)
        self.assertEqual(out["sector"], "Energy")
        self.assertEqual(out["industry"], "Oil & Gas Equipment & Services")

    def test_does_not_mutate_complete_current_identity(self):
        current = {"ticker": "LLY", "sector": "Healthcare", "industry": "Biotechnology"}
        fallback = {
            "sector": "Consumer Defensive",
            "industry": "Drug Manufacturers - General",
        }
        out = apply_market_identity_fallback(current, fallback)
        self.assertIs(out, current)
        self.assertEqual(out["sector"], "Healthcare")
        self.assertEqual(out["industry"], "Biotechnology")

    def test_missing_fallback_does_nothing(self):
        current = {"ticker": "NEW", "sector": None, "industry": None}
        out = apply_market_identity_fallback(current, None)
        self.assertIs(out, current)


if __name__ == "__main__":
    unittest.main(verbosity=2)
