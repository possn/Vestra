"""Guard against indefinite Dashboard news staleness during long-running UI PR work."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "update-dashboard-feeds.yml"


class NewsPublishWindowTests(unittest.TestCase):
    def test_overdue_news_bypasses_regular_code_pr_deferral(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("age >= 90 * 60", content)
        self.assertIn("git', 'show', 'HEAD:data/dashboard-news.json'", content)
        self.assertIn(
            "steps.publish_window.outputs.defer != 'true' || steps.news_freshness.outputs.overdue == 'true'",
            content,
        )


if __name__ == "__main__":
    unittest.main()
