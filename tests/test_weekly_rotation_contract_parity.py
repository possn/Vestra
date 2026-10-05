from pathlib import Path
import ast
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def _frontend_contract(source: str):
    themes_block = source.split("const WEEKLY_ROTATION_THEMES=[", 1)[1].split("];", 1)[0]
    themes = [
        (label, pattern)
        for label, pattern in re.findall(r"\['([^']+)',/([^/]+)/i\]", themes_block)
    ]

    etf_block = source.split("const WEEKLY_ROTATION_ETFS={", 1)[1].split("};", 1)[0]
    etfs = {}
    for label, raw in re.findall(r"'([^']+)':\[([^\]]*)\],", etf_block):
        etfs[label] = tuple(re.findall(r"'([^']+)'", raw))
    return [(label, pattern, etfs.get(label, ())) for label, pattern in themes]


def _backend_contract(source: str):
    module = ast.parse(source)
    assignment = next(
        node for node in module.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "ROTATION_THEMES" for target in node.targets)
    )
    rows = []
    for item in assignment.value.elts:
        label = item.elts[0].value
        compile_call = item.elts[1]
        pattern = compile_call.args[0].value
        tickers = tuple(elt.value for elt in item.elts[2].elts)
        rows.append((label, pattern, tickers))
    return rows


class WeeklyRotationContractParityTests(unittest.TestCase):
    def setUp(self):
        self.market = (ROOT / "market.js").read_text(encoding="utf-8")
        self.backend = (ROOT / "scripts" / "postprocess_market.py").read_text(encoding="utf-8")

    def test_theme_patterns_and_etf_baskets_match_backend_exactly(self):
        self.assertEqual(_frontend_contract(self.market), _backend_contract(self.backend))

    def test_price_signal_thresholds_match_backend(self):
        pairs = (
            ("med5>=2&&breadth>=60", "med5 >= 2 and breadth >= 60"),
            ("med5>=.5&&breadth>=55", "med5 >= .5 and breadth >= 55"),
            ("med5<=-2&&breadth<=40", "med5 <= -2 and breadth <= 40"),
            ("med5<=-.5&&breadth<=45", "med5 <= -.5 and breadth <= 45"),
        )
        for frontend, backend in pairs:
            with self.subTest(frontend=frontend):
                self.assertIn(frontend, self.market)
                self.assertIn(backend, self.backend)

    def test_etf_confirmation_is_fail_closed_on_both_sides(self):
        self.assertIn("directional.every(sign=>sign===expectedSign)", self.market)
        self.assertIn("expectedSign!==1&&expectedSign!==-1", self.market)
        self.assertIn(
            'expected_sign = 1 if signal in {"strong_inflow","inflow"} else -1 if signal in {"strong_outflow","outflow"} else 0',
            self.backend,
        )
        self.assertIn("etf_confirmed = bool(all(agrees))", self.backend)

    def test_rotation_return_window_is_five_observations_on_both_paths(self):
        self.assertIn("closes[closes.length-6]", self.market)
        self.assertIn("_weekly_return(row)", self.backend)
        self.assertIn("closes[-6]", self.backend)


if __name__ == "__main__":
    unittest.main(verbosity=2)
