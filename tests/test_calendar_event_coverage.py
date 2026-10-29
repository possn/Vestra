from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class CalendarCoverageTests(unittest.TestCase):
    def test_company_earnings_are_not_discarded_by_macro_first_cap(self):
        js = (ROOT / 'dashboard-weekly-events.js').read_text(encoding='utf-8')
        self.assertIn('const MAX_EVENTS = 40;', js)
        self.assertIn('[...portfolioEarnings, ...macroEvents.sort(', js)
        self.assertIn('...marketEarnings].slice(0, cap)', js)
        self.assertIn('Sem eventos confirmados nesta semana.', js)
        self.assertIn("loadCalendarStartupStocks()", js)
        self.assertIn("unpackStartupPayload", js)
        self.assertNotIn("sourceStatus.textContent", js)
        self.assertIn("const VERSION = '3.7';", js)

    def test_critical_macro_precedes_earnings_in_collapsed_week_and_fomc_exists(self):
        js = (ROOT / 'dashboard-weekly-events.js').read_text(encoding='utf-8')
        loader = (ROOT / 'market-static-universe.js').read_text(encoding='utf-8')
        self.assertIn("const criticalMacro = events.filter(event => event.kind === 'macro' &&", js)
        self.assertIn("event.importance === 'critical');", js)
        self.assertNotIn("event.importance === 'critical' && event.date >= localDay(now)", js)
        self.assertIn("Keep critical official macro events visible for the whole calendar week", js)
        self.assertIn("const displayEvents = [...retained, ...criticalMacro, ...priority, ...secondary]", js)
        self.assertIn("const stillThisWeek = pinned", js)
        self.assertIn("displayEvents.slice(0,COLLAPSED_EVENTS)", js)
        self.assertIn("dashboard-weekly-events.js?v=3.7", loader)

    def test_calendar_recovers_late_startup_earnings_and_uses_short_status(self):
        runtime = (ROOT / 'dashboard-weekly-events.js').read_text(encoding='utf-8')
        sw = (ROOT / 'sw.js').read_text(encoding='utf-8')
        self.assertIn("if (!options.stocks && !stocks.length && !calendarStartupLoading)", runtime)
        self.assertIn("loadCalendarStartupStocks().then(loaded => { if (loaded?.length) render(expandedContext || {}); })", runtime)
        self.assertIn("A carregar resultados das empresas…", runtime)
        self.assertNotIn("Cobertura de resultados: índice de empresas ainda indisponível", runtime)
        self.assertRegex(sw, r'const CACHE_NAME = "vestra-cache-v\d+"')

    def test_historical_earnings_archive_is_loaded_without_overwriting_live_stock_dates(self):
        js = (ROOT / 'dashboard-weekly-events.js').read_text(encoding='utf-8')
        self.assertIn('function combineArchivedStocks(stocks, archive)', js)
        self.assertIn('if (keys.has(key))', js)
        self.assertIn('number(merged[index]?.analyst_latest_eps_actual) === null', js)
        self.assertIn('merged[index] = { ...merged[index], ...archiveFields }', js)
        self.assertIn('loadEarningsArchive()', js)
        self.assertIn("data/earnings-events.json", js)
        self.assertIn('combineArchivedStocks(mergeLatestEarnings(stocks, latestEarnings), earningsArchive)', js)
        self.assertIn('vestra_earnings_events_v1', js)

    def test_historical_official_dates_retained_for_three_months(self):
        script = (ROOT / 'scripts/update_macro_events.py').read_text(encoding='utf-8')
        self.assertIn('recent_floor = iso(today - timedelta(days=90))', script)
        self.assertIn('if d < today - timedelta(days=90)', script)
        self.assertIn('if str(e.get("date", "")) >= iso(today - timedelta(days=90))', script)

if __name__ == '__main__':
    unittest.main()
