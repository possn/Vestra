import unittest

from zombie_risk import classify_zombie_risk


def row(ebit, interest, fcf=10, debt=50, cash=20):
    return {
        "ebit": ebit, "interest_expense": interest, "free_cash_flow": fcf,
        "total_debt": debt, "total_cash": cash,
    }


class ZombieRiskTests(unittest.TestCase):
    def test_one_bad_year_is_only_fragile(self):
        r = classify_zombie_risk([row(5,10), row(20,10), row(25,10)])
        self.assertEqual(r["state"], "fragile")
        self.assertEqual(r["years_below_one"], 1)

    def test_two_bad_years_are_candidate_not_probable(self):
        r = classify_zombie_risk([row(5,10), row(6,10), row(20,10)])
        self.assertEqual(r["state"], "candidate")

    def test_three_bad_years_need_financing_dependence(self):
        no_support = classify_zombie_risk([
            row(5,10,fcf=5,debt=10,cash=100),
            row(6,10,fcf=5,debt=10,cash=100),
            row(7,10,fcf=5,debt=10,cash=100),
        ])
        self.assertEqual(no_support["state"], "candidate")

        probable = classify_zombie_risk([
            row(5,10,fcf=-5,debt=100,cash=10),
            row(6,10,fcf=-4,debt=90,cash=10),
            row(7,10,fcf=2,debt=80,cash=10),
        ])
        self.assertEqual(probable["state"], "probable")
        self.assertGreaterEqual(probable["years_below_one"], 3)

    def test_banks_are_not_classified_by_generic_interest_coverage(self):
        r = classify_zombie_risk([row(5,10), row(5,10), row(5,10)], sector="Financial Services", industry="Banks")
        self.assertEqual(r["state"], "not_applicable")


if __name__ == "__main__":
    unittest.main()
