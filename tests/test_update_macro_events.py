import importlib.util
from datetime import date
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DEPS_AVAILABLE = all(importlib.util.find_spec(name) is not None for name in ('pandas', 'requests', 'lxml'))
mod = None
if DEPS_AVAILABLE:
    SPEC = importlib.util.spec_from_file_location('update_macro_events', ROOT / 'scripts' / 'update_macro_events.py')
    mod = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(mod)


class _Response:
    def __init__(self, text, status=200):
        self.text = text
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f'HTTP {self.status_code}')


class _Session:
    def __init__(self, text):
        self.text = text

    def get(self, *args, **kwargs):
        return _Response(self.text)


@unittest.skipUnless(DEPS_AVAILABLE, 'macro refresher dependencies are installed only in the dedicated workflow')
class MacroCalendarTests(unittest.TestCase):
    def test_bls_ics_extracts_only_high_signal_releases(self):
        ics = '''BEGIN:VCALENDAR\nBEGIN:VEVENT\nDTSTART:20261014T083000\nSUMMARY:Consumer Price Index for September 2026\nEND:VEVENT\nBEGIN:VEVENT\nDTSTART:20261015T083000\nSUMMARY:Producer Price Index for September 2026\nEND:VEVENT\nBEGIN:VEVENT\nDTSTART:20261002T083000\nSUMMARY:Employment Situation for September 2026\nEND:VEVENT\nBEGIN:VEVENT\nDTSTART:20261005T100000\nSUMMARY:Minor Statistical Release for September 2026\nEND:VEVENT\nEND:VCALENDAR\n'''
        events = mod.bls_events(_Session(ics))
        self.assertEqual([e['short_title'] for e in events], ['CPI EUA', 'PPI EUA', 'NFP EUA'])
        self.assertEqual(events[0]['date'], '2026-10-14')
        self.assertEqual(events[0]['time_local'], '08:30 ET')
        self.assertEqual(events[2]['importance'], 'critical')

    def test_validate_events_is_fail_closed_and_deduplicates(self):
        today = date(2026, 9, 6)
        event = {
            'date': '2026-09-16', 'title': 'FOMC', 'short_title': 'FOMC',
            'category': 'central_bank', 'region': 'EUA', 'importance': 'critical', 'source': 'fed'
        }
        valid = mod.validate_events('fed', [event, dict(event)], today)
        self.assertEqual(len(valid), 1)
        with self.assertRaises(RuntimeError):
            mod.validate_events('fed', [{**event, 'date': '2026-01-01'}], today)
        with self.assertRaises(RuntimeError):
            mod.validate_events('fed', [{**event, 'source': 'bls'}], today)

    def test_source_catalog_is_official_and_complete(self):
        self.assertEqual(set(mod.ADAPTERS), {'fed', 'bls', 'bea', 'ecb', 'census'})
        for key, (_, url) in mod.SOURCES.items():
            self.assertTrue(url.startswith('https://'), key)
            self.assertIn(key if key != 'fed' else 'federalreserve', url.lower())


class MacroCalendarStaticTests(unittest.TestCase):
    def test_refresher_source_declares_official_catalog_and_fail_closed_fallback(self):
        source = (ROOT / 'scripts' / 'update_macro_events.py').read_text(encoding='utf-8')
        for token in ('federalreserve.gov', 'bls.gov', 'bea.gov', 'ecb.europa.eu', 'census.gov'):
            self.assertIn(token, source)
        self.assertIn('no plausible future events', source)
        self.assertIn('refresh failed and no validated fallback exists', source)


if __name__ == '__main__':
    if not DEPS_AVAILABLE:
        print('macro calendar functional tests skipped in dependency-free historical suite')
    unittest.main(verbosity=2)
