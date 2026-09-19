from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StartupScriptDeferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = (ROOT / "index.html").read_text(encoding="utf-8")

    def script_tag(self, src_fragment):
        pattern = re.compile(r"<script(?P<attrs>[^>]*)src=[\"'][^\"']*" + re.escape(src_fragment) + r"[^\"']*[\"'](?P<tail>[^>]*)></script>")
        match = pattern.search(self.index)
        self.assertIsNotNone(match, src_fragment)
        return (match.group("attrs") + " " + match.group("tail")).strip()

    def test_chartjs_does_not_block_html_parser(self):
        attrs = self.script_tag("chart.umd.min.js")
        self.assertRegex(attrs, r"\bdefer\b")

    def test_lazy_xlsx_loader_is_deferred_too(self):
        attrs = self.script_tag("app-xlsx-loader.js?v=1.0")
        self.assertRegex(attrs, r"\bdefer\b")

    def test_chartjs_stays_before_app_runtime(self):
        chart = self.index.index("chart.umd.min.js")
        app = self.index.index("app.js?v=20260919v3")
        self.assertLess(chart, app)
        self.assertIn('defer="" fetchpriority="high"', self.index[self.index.index("<script", app - 80):app + 120])


if __name__ == "__main__":
    unittest.main(verbosity=2)
