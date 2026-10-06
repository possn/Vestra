import unittest
from types import SimpleNamespace

from scripts.zombie_risk import assess


def company(history, **overrides):
    base = dict(quote_type='EQUITY', sector='Technology', industry='Software', total_debt=100.0, total_cash=20.0, annual_zombie_history=history)
    base.update(overrides)
    return SimpleNamespace(**base)


def row(year, coverage, fcf=10.0, debt=100.0, cash=20.0):
    interest = 10.0
    return {'date': f'{year}-12-31', 'ebit': coverage * interest, 'interest_expense': interest, 'interest_coverage': coverage, 'free_cash_flow': fcf, 'total_debt': debt, 'total_cash': cash}


class ZombieRiskTests(unittest.TestCase):
    def test_probable_requires_persistence_and_supporting_stress(self):
        m = company([row(2025, .6, -5), row(2024, .7), row(2023, .8)])
        assess(m)
        self.assertEqual(m.zombie_risk_status, 'probable')
        self.assertEqual(m.zombie_risk_weak_years, 3)

    def test_two_consecutive_weak_years_is_candidate_not_probable(self):
        m = company([row(2025, .6), row(2024, .9), row(2023, 1.5)])
        assess(m)
        self.assertEqual(m.zombie_risk_status, 'candidate')

    def test_one_weak_year_is_fragile(self):
        m = company([row(2025, .8), row(2024, 1.4), row(2023, 1.5)])
        assess(m)
        self.assertEqual(m.zombie_risk_status, 'fragile')

    def test_missing_history_fails_closed(self):
        m = company([row(2025, .8)])
        assess(m)
        self.assertEqual(m.zombie_risk_status, 'unavailable')

    def test_banks_are_not_classified_by_generic_interest_coverage(self):
        m = company([row(2025, .4), row(2024, .5), row(2023, .6)], sector='Financial Services', industry='Banks')
        assess(m)
        self.assertEqual(m.zombie_risk_status, 'not_applicable')

    def test_clear_when_coverage_is_consistently_above_one(self):
        m = company([row(2025, 2.2), row(2024, 1.8), row(2023, 1.4)])
        assess(m)
        self.assertEqual(m.zombie_risk_status, 'clear')


if __name__ == '__main__':
    unittest.main()
