from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'scripts' / 'macro_calendar_transport.py').read_text(encoding='utf-8')
WORKFLOW = (ROOT / '.github' / 'workflows' / 'update-macro-events.yml').read_text(encoding='utf-8')


class MacroCalendarTransportTests(unittest.TestCase):
    def test_census_uses_session_backed_html_before_table_parse(self):
        self.assertIn('page = base.fetch_text(session, url)', SOURCE)
        self.assertIn('pd.read_html(StringIO(page))', SOURCE)
        self.assertIn('base.ADAPTERS["census"] = census_events', SOURCE)

    def test_bls_keeps_primary_official_paths_then_fred_mirror(self):
        self.assertIn('events = base.bls_events(session)', SOURCE)
        self.assertIn('https://www.bls.gov/schedule/{year}/', SOURCE)
        self.assertIn('https://fred.stlouisfed.org/releases/calendar?rid=', SOURCE)
        self.assertIn('schedule_transport": "fred_stlouisfed"', SOURCE)
        self.assertIn('base.ADAPTERS["bls"] = bls_events', SOURCE)
        for release_id in ('10:', '46:', '50:', '192:'):
            self.assertIn(release_id, SOURCE)

    def test_workflow_runs_hardened_transport_without_touching_market_pipeline(self):
        self.assertIn('scripts/macro_calendar_transport.py', WORKFLOW)
        self.assertIn('PYTHONPATH=scripts python scripts/macro_calendar_transport.py', WORKFLOW)
        self.assertNotIn('run_market_pipeline.py', WORKFLOW)


if __name__ == '__main__':
    unittest.main(verbosity=2)
