from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class CalendarCoverageTests(unittest.TestCase):
    def test_company_earnings_are_not_discarded_by_macro_first_cap(self):
        js = (ROOT / 'dashboard-weekly-events.js').read_text(encoding='utf-8')
        self.assertIn('const MAX_EVENTS = 40;', js)
        self.assertIn('[...portfolioEarnings, ...macroEvents.sort(', js)
        self.assertIn('...marketEarnings].slice(0, cap)', js)
        self.assertIn('Sem eventos confirmados neste intervalo', js)
        self.assertIn("data/stocks-startup.json", js)
        self.assertIn("async function loadEarningsStocks", js)
        self.assertIn("earningsStockCache", js)
        self.assertIn("Sem eventos com data nesta semana.", js)
        self.assertNotIn('Cobertura de resultados: índice de empresas ainda indisponível', js)
        self.assertIn("const VERSION = '3.1';", js)

    def test_historical_official_dates_retained_for_three_months(self):
        script = (ROOT / 'scripts/update_macro_events.py').read_text(encoding='utf-8')
        self.assertIn('recent_floor = iso(today - timedelta(days=90))', script)
        self.assertIn('if d < today - timedelta(days=90)', script)
        self.assertIn('if str(e.get("date", "")) >= iso(today - timedelta(days=90))', script)

if __name__ == '__main__':
    unittest.main()
