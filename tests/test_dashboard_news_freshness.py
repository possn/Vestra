"""Dashboard news must never label expired RSS headlines as current."""
import sys
import unittest
import datetime
import email.utils
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import news


def headline(title, age_hours):
    stamp = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=age_hours)
    return {"title": title, "link": "https://example.org/story",
            "published": email.utils.format_datetime(stamp), "source": "Example"}


class DashboardNewsFreshnessTests(unittest.TestCase):
    def test_excludes_expired_and_undated_articles(self):
        corpus = {
            "JPM": [
                headline("JPM earnings published recently", 2),
                headline("JPM old corporate update", 120),
                {"title":"JPM unknown timestamp","link":"https://example.org/unknown",
                 "published":"","source":"Example"},
            ]
        }
        with patch.object(news, "_rss_items", return_value=[]):
            result = news._build_dashboard_digest(corpus)
        self.assertEqual([row["title"] for row in result["items"]],
                         ["JPM earnings published recently"])
        self.assertEqual(result["fresh_items"], 1)
        self.assertEqual(result["freshness_window_hours"], 72)

    def test_empty_feed_does_not_recycle_old_headlines(self):
        with patch.object(news, "_rss_items", return_value=[]):
            result = news._build_dashboard_digest({
                "GS": [headline("GS stale story", 168)]
            })
        self.assertEqual(result["items"], [])
        self.assertEqual(result["fresh_items"], 0)


if __name__ == "__main__":
    unittest.main()
