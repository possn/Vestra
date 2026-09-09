from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'dashboard-weekly-events.js').read_text(encoding='utf-8')


class DashboardWeeklyMacroSummaryTests(unittest.TestCase):
    def test_snapshot_maps_verified_summary_fields(self):
        self.assertIn("resultSummary: text(row?.result_summary)", SOURCE)
        self.assertIn("resultReleasedAt: text(row?.result_released_at)", SOURCE)
        self.assertIn("sourceUrl: officialSourceUrl(source, row?.source_url)", SOURCE)

    def test_official_summary_is_not_treated_as_an_invented_actual(self):
        self.assertIn("text(event?.resultStatus) === 'official_release_summary'", SOURCE)
        self.assertIn("hasMacroResult(event) || hasOfficialMacroSummary(event)", SOURCE)
        self.assertIn("if (hasMacroMetrics(event))", SOURCE)
        self.assertIn("sem inferir uma métrica “Actual” ambígua", SOURCE)

    def test_summary_is_rendered_as_text_and_official_link_stays_hardened(self):
        self.assertIn("body.textContent = text(summary)", SOURCE)
        self.assertNotIn("body.innerHTML = summary", SOURCE)
        self.assertIn("if (hasSummary) sheet.appendChild(officialSummary(event.resultSummary));", SOURCE)
        self.assertIn("action.rel = 'noopener noreferrer'", SOURCE)
        self.assertIn("parsed.protocol !== 'https:'", SOURCE)


if __name__ == '__main__':
    unittest.main(verbosity=2)
