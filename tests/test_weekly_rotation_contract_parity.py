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
        self.assertIn("flowSign===expectedSign?true:null", self.market)
        self.assertIn(
            'expected_sign = 1 if signal in {"strong_inflow","inflow"} else -1 if signal in {"strong_outflow","outflow"} else 0',
            self.backend,
        )
        self.assertIn("if not all(agrees):", self.backend)
        self.assertIn("elif etf_flow is not None and etf_flow != 0:", self.backend)
        self.assertIn("etf_confirmed = True", self.backend)

    def test_rotation_return_window_is_five_observations_on_both_paths(self):
        self.assertIn("closes[closes.length-6]", self.market)
        self.assertIn("weekly = [(r, _weekly_return(r)) for r in members]", self.backend)
        self.assertIn("closes[-6]", self.backend)

    def test_backend_prefers_price_history_before_opportunity_fallback(self):
        weekly = self.backend.split("def _weekly_return(row: dict):", 1)[1].split("def _rotation_context", 1)[0]
        history_return = 'return (closes[-1] / closes[-6] - 1.0) * 100.0'
        fallback = 'return _n(row.get("opportunity_return_5d_pct"))'
        self.assertIn("if len(closes) > 5:", weekly)
        self.assertIn(history_return, weekly)
        self.assertIn(fallback, weekly)
        self.assertLess(weekly.index(history_return), weekly.index(fallback))

    def test_backend_recomputes_current_run_etf_flow_before_rotation_context(self):
        self.assertIn(
            "from build_market_shards import fund_flow_metrics, load_fund_aum_history, update_fund_aum_history",
            self.backend,
        )
        main = self.backend.split("def main() -> None:", 1)[1]
        history_call = "fund_history = update_fund_aum_history(rows, as_of, load_fund_aum_history())"
        rotation_call = "rotation_contexts = _rotation_context(rows, fund_history=fund_history, as_of=as_of)"
        self.assertIn(history_call, main)
        self.assertIn(rotation_call, main)
        self.assertLess(main.index(history_call), main.index(rotation_call))
        rotation = self.backend.split('def _rotation_context(rows, fund_history=None, as_of=""):', 1)[1].split(
            "def _attach_rotation_context", 1
        )[0]
        self.assertIn("fund_flow_metrics(x, fund_history or {}, as_of)", rotation)
        self.assertNotIn('x.get("fund_flow_1w_usd")', rotation)


if __name__ == "__main__":
    unittest.main(verbosity=2)
