from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


class PortfolioDiagnosticsTests(unittest.TestCase):
    def test_diagnosis_state_survives_portfolio_ui_rerenders(self):
        s = read('portfolio-diagnostics.js')
        self.assertIn("c.dataset.vpdDiagnosis==='1'", s)
        self.assertIn("dc.hidden=!open", s)
        self.assertIn("data-vpu-detail", s)
        self.assertIn("syncDiagnosis(c)", s)

    def test_count_coverage_is_distinct_from_value_coverage(self):
        s = read('portfolio-diagnostics.js')
        self.assertIn("Math.round(research/positions*100)", s)
        self.assertIn("Cobertura por valor", s)
        self.assertIn("Cobertura posições", s)
        self.assertIn("do valor", s)

    def test_overlap_reports_data_coverage_instead_of_false_zero(self):
        s = read('portfolio-diagnostics.js')
        self.assertIn("TOP OVERLAP DETETADO", s)
        self.assertIn("ETFs com holdings detalhados", s)
        self.assertIn("Isto não significa necessariamente overlap zero", s)
        self.assertIn("Mostramos os maiores sinais mesmo abaixo dos antigos cortes de 5%/2%", s)
        self.assertIn("AÇÃO + ETF", s)
        self.assertIn("ETF × ETF", s)

    def test_diagnostics_load_after_portfolio_ui_and_are_cached(self):
        h = read('index.html')
        sw = read('sw.js')
        self.assertLess(h.index('vestra-portfolio-ui.js'), h.index('portfolio-diagnostics.js'))
        self.assertIn("portfolio-diagnostics.js?v=1.0", h)
        self.assertIn('./portfolio-diagnostics.js', sw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
