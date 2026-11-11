"""Congress feed freshness must reject future-dated and stale disclosures."""
import datetime as dt
import unittest

from scripts.congress import _is_fresh, MAX_STALE_DAYS


class CongressFreshnessTests(unittest.TestCase):
    def _snapshot(self, day):
        return {"schema_version": 2, "newest_disclosure": day.isoformat()}

    def test_malformed_schema_fails_closed_without_crashing(self):
        recent = dt.date.today() - dt.timedelta(days=2)
        for bad in ("not-a-number", {}, [], {"version": 2}, float("inf")):
            with self.subTest(schema=repr(bad)):
                self.assertFalse(_is_fresh({
                    "schema_version": bad,
                    "newest_disclosure": recent.isoformat()
                }))

    def test_recent_disclosure_is_fresh(self):
        self.assertTrue(_is_fresh(self._snapshot(dt.date.today() - dt.timedelta(days=2))))

    def test_future_disclosure_is_not_fresh(self):
        self.assertFalse(_is_fresh(self._snapshot(dt.date.today() + dt.timedelta(days=1))))

    def test_stale_disclosure_is_not_fresh(self):
        self.assertFalse(_is_fresh(self._snapshot(
            dt.date.today() - dt.timedelta(days=MAX_STALE_DAYS + 1))))

    def test_unparseable_disclosure_is_not_fresh(self):
        self.assertFalse(_is_fresh({"schema_version": 2, "newest_disclosure": "bad"}))


if __name__ == "__main__":
    unittest.main()
