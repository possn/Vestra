#!/usr/bin/env python3
"""Synthetic contract tests only; never establish predictive accuracy."""
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from prospective_shadow_journal import append_signal, validate_signal

NOW = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)
SIGNAL = {
    "issuer_id": "test-instrument-1",
    "signal_session": "2026-10-26",
    "model_version": "hypothesis-v0",
    "rule_id": "compression-watch",
    "source": "synthetic-contract-test",
    "source_available_at_utc": "2026-10-26T11:00:00Z",
    "features_sha256": hashlib.sha256(b"fixed-features").hexdigest(),
}


class ProspectiveJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "private" / "signals.jsonl"

    def test_first_record_then_idempotent(self):
        first = append_signal(self.path, SIGNAL, now=NOW)
        self.assertEqual(first["status"], "RECORDED_UNVALIDATED_SIGNAL")
        self.assertEqual(append_signal(self.path, SIGNAL, now=NOW)["status"], "ALREADY_RECORDED")
        self.assertEqual(len(self.path.read_text().splitlines()), 1)

    def test_conflicting_replay_rejected(self):
        append_signal(self.path, SIGNAL, now=NOW)
        changed = dict(SIGNAL, features_sha256="0" * 64)
        with self.assertRaisesRegex(ValueError, "conflicting replay"):
            append_signal(self.path, changed, now=NOW)

    def test_modified_chain_detected(self):
        append_signal(self.path, SIGNAL, now=NOW)
        modified = json.loads(self.path.read_text())
        modified["signal"]["source"] = "tampered"
        self.path.write_text(json.dumps(modified) + "\n")
        with self.assertRaisesRegex(ValueError, "broken journal hash chain"):
            append_signal(self.path, dict(SIGNAL, issuer_id="second"), now=NOW)

    def test_future_source_rejected(self):
        with self.assertRaisesRegex(ValueError, "future source"):
            validate_signal(dict(SIGNAL, source_available_at_utc="2026-10-27T00:00:00Z"),
                            capture_at_utc=NOW.isoformat())

    def test_future_signal_rejected(self):
        with self.assertRaisesRegex(ValueError, "future signal"):
            validate_signal(dict(SIGNAL, signal_session="2026-10-27"),
                            capture_at_utc=NOW.isoformat())

    def test_invalid_features_digest_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid feature hash"):
            validate_signal(dict(SIGNAL, features_sha256="unknown"),
                            capture_at_utc=NOW.isoformat())

    def test_naive_capture_clock_rejected(self):
        with self.assertRaisesRegex(ValueError, "naive capture"):
            append_signal(self.path, SIGNAL, now=datetime(2026, 10, 26))

    def test_nonfrozen_fields_rejected(self):
        with self.assertRaisesRegex(ValueError, "unexpected"):
            validate_signal(dict(SIGNAL, success_probability=.89),
                            capture_at_utc=NOW.isoformat())

    def test_second_issuer_appends_chain(self):
        append_signal(self.path, SIGNAL, now=NOW)
        second = append_signal(self.path, dict(SIGNAL, issuer_id="second"), now=NOW)
        self.assertEqual(second["status"], "RECORDED_UNVALIDATED_SIGNAL")
        entries = [json.loads(x) for x in self.path.read_text().splitlines()]
        self.assertEqual(entries[1]["previous_sha256"], entries[0]["record_sha256"])

if __name__ == "__main__":
    unittest.main()
