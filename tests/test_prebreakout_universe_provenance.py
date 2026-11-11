"""As-of universe provenance must be auditable without claiming signal edge."""
import hashlib
import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("prebreakout", ROOT/"scripts/refresh_prebreakout_scanner.py")
scanner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)


def stock(ticker,cap=600_000_000):
    return {"ticker":ticker,"market_cap":cap,"quote_type":"EQUITY"}


class UniverseProvenanceTests(unittest.TestCase):
    def test_hash_is_stable_under_index_reordering_and_duplicates(self):
        source=b'{"stocks":[]}'
        left=scanner.universe_provenance_audit([stock("B"),stock("A"),stock("A")],{},source)
        right=scanner.universe_provenance_audit([stock("A"),stock("B")],{},source)
        expected=hashlib.sha256(b"A\nB").hexdigest()
        self.assertEqual(left["eligible_tickers_sha256"],expected)
        self.assertEqual(right["eligible_tickers_sha256"],expected)
        self.assertEqual(left["source_index_sha256"],hashlib.sha256(source).hexdigest())
        self.assertEqual(left["eligible_count"],2)
        self.assertIsNone(left["membership_changed"])
        self.assertEqual(left["membership_comparison"],"unknown_prior_fingerprint")

    def test_membership_change_detected_without_equating_count_to_identity(self):
        prior=scanner.universe_provenance_audit([stock("A"),stock("B")],{},b"one")
        old={"eligible_universe":2,"universe_provenance_audit":prior}
        unchanged=scanner.universe_provenance_audit([stock("B"),stock("A")],old,b"two")
        changed=scanner.universe_provenance_audit([stock("A"),stock("C")],old,b"three")
        self.assertFalse(unchanged["membership_changed"])
        self.assertTrue(changed["membership_changed"])
        self.assertEqual(changed["eligible_count_change"],0)
        self.assertEqual(changed["previous_eligible_count"],2)

    def test_legacy_report_has_unknown_membership_even_when_count_moves(self):
        result=scanner.universe_provenance_audit([stock("A")],{"eligible_universe":1272},b"index")
        self.assertEqual(result["eligible_count_change"],-1271)
        self.assertIsNone(result["membership_changed"])
        self.assertEqual(result["membership_comparison"],"unknown_prior_fingerprint")
        self.assertTrue(result["coverage_is_not_signal_performance"])


if __name__=="__main__":
    unittest.main()
