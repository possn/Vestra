from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ROUTER = (ROOT / "worker-router.js").read_text(encoding="utf-8")
VERIFIER = (ROOT / "scripts" / "verify_sec_transport_deployment.py").read_text(encoding="utf-8")


class SecTransportHealthSemanticsTests(unittest.TestCase):
    def test_sec_transport_is_not_advertised_as_operational_capability(self):
        self.assertIn("experimental_capabilities:experimentalCapabilities", ROUTER)
        self.assertIn("status:'experimental_not_in_pipeline'", ROUTER)
        self.assertIn("SEC_TRANSPORT_CAPABILITY", ROUTER)
        self.assertNotIn("'learned_universe','ai_brief',SEC_TRANSPORT_CAPABILITY]", ROUTER)

    def test_verifier_only_tolerates_known_sec_upstream_403(self):
        self.assertIn('diagnostic.get("upstream_status") == 403', VERIFIER)
        self.assertIn('response.status_code == 502', VERIFIER)
        self.assertIn('diagnostic.get("error") == "SEC upstream indisponível"', VERIFIER)
        self.assertIn('"sec_transport" not in capabilities', VERIFIER)
        self.assertIn('"sec_transport" in experimental', VERIFIER)
        self.assertIn('return 1 if failures else 0', VERIFIER)


if __name__ == "__main__":
    unittest.main(verbosity=2)
