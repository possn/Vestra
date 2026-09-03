from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import sec_endpoint_probe


def make_report(statuses, http_ok=0):
    names = ("AAPL", "MSFT", "NVDA")
    rows = {}
    values = iter(statuses)
    for idx, ticker in enumerate(names, start=1):
        rows[ticker] = {
            "cik": idx,
            "companyfacts": {"status": next(values), "ok": False},
            "submissions": {"status": next(values), "ok": False},
        }
    return {
        "sentinels": rows,
        "summary": {"requests": 6, "http_ok": http_ok, "payload_ok": 0},
    }


class SecProbeRuntimePolicyTests(unittest.TestCase):
    def test_uniform_403_marks_following_sec_step_for_skip(self):
        payload = make_report([403, 403, 403, 403, 403, 403])
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / "github_env"
            self.assertTrue(sec_endpoint_probe.apply_runtime_guard(payload, env_path=env_path))
            self.assertEqual(env_path.read_text(encoding="utf-8"), "SEC_USER_AGENT=\n")

    def test_mixed_statuses_keep_sec_step_available(self):
        payload = make_report([403, 403, 403, 500, 403, 403])
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / "github_env"
            self.assertFalse(sec_endpoint_probe.apply_runtime_guard(payload, env_path=env_path))
            self.assertFalse(env_path.exists())

    def test_transport_error_is_not_treated_as_uniform_403(self):
        payload = make_report([403, 403, 403, 0, 403, 403])
        self.assertFalse(sec_endpoint_probe._runtime_sec_blocked(payload))

    def test_any_success_keeps_sec_step_available(self):
        payload = make_report([403, 403, 403, 200, 403, 403], http_ok=1)
        self.assertFalse(sec_endpoint_probe._runtime_sec_blocked(payload))

    def test_incomplete_identity_probe_keeps_sec_step_available(self):
        payload = make_report([403, 403, 403, 403, 403, 403])
        payload["sentinels"]["NVDA"]["cik"] = None
        self.assertFalse(sec_endpoint_probe._runtime_sec_blocked(payload))


if __name__ == "__main__":
    unittest.main(verbosity=2)
