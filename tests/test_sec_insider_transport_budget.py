"""Bound SEC timeout cost without converting missing filings into zero activity."""
import os
import unittest
from unittest.mock import patch

from scripts import insiders


class TransportBudgetTests(unittest.TestCase):
    def test_retries_default_unchanged(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FINSCANNER_SEC_HTTP_RETRIES", None)
            retries = insiders._session().get_adapter("https://").max_retries
            self.assertEqual(retries.total, 4)
            self.assertEqual(retries.read, 4)

    def test_workflow_can_bound_archive_retries(self):
        with patch.dict(os.environ, {"FINSCANNER_SEC_HTTP_RETRIES": "0"}):
            retries = insiders._session().get_adapter("https://").max_retries
            self.assertEqual(retries.total, 0)
            self.assertEqual(retries.read, 0)

    def test_only_archive_documents_get_shorter_timeout(self):
        class Session:
            def __init__(self):
                self.calls = []

            def get(self, url, timeout):
                self.calls.append((url, timeout))
                return self

            def raise_for_status(self):
                pass

        session = Session()
        archive = "https://www.sec.gov/Archives/edgar/data/123/456/filing.txt"
        submissions = "https://data.sec.gov/submissions/CIK0000000123.json"
        with patch.dict(os.environ, {"FINSCANNER_SEC_ARCHIVE_TIMEOUT": "10"}), \
             patch.object(insiders, "_get_session", return_value=session), \
             patch.object(insiders, "_throttle"):
            insiders._get(archive)
            insiders._get(submissions)
        self.assertEqual(session.calls, [(archive, 10), (submissions, 25)])


if __name__ == "__main__":
    unittest.main()
