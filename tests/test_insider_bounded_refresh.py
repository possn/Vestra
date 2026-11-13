"""SEC issuer rotation must preserve honest unknown coverage and fair rotation."""
import ast
from datetime import date, timedelta
from pathlib import Path
import unittest


ROOT=Path(__file__).resolve().parents[1]
RUN=(ROOT/"scripts/run.py").read_text(encoding="utf-8")
WORKFLOW=(ROOT/".github/workflows/update-market-data.yml").read_text(encoding="utf-8")


def load_selector():
    tree=ast.parse(RUN)
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
            and n.name=="_insider_refresh_selection")
    ns={}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),"run.py","exec"),ns)
    return ns["_insider_refresh_selection"]


class InsiderBoundedRefreshTests(unittest.TestCase):
    def test_daily_rotation_covers_full_stable_universe(self):
        select=load_selector()
        names=[f"T{i:03d}" for i in range(346)]
        start=date(2026,11,13)
        batches=[select(names,120,start+timedelta(days=i)) for i in range(3)]
        self.assertEqual([len(x) for x in batches],[120]*3)
        self.assertEqual(set().union(*(set(x) for x in batches)),set(names))
        self.assertTrue(all(len(set(x))==len(x) for x in batches))

    def test_small_universe_not_truncated_or_duplicated(self):
        select=load_selector()
        self.assertEqual(select(["B","A","A"],120,date(2026,11,13)),["A","B"])
        with self.assertRaises(ValueError):select(["A"],0,date(2026,11,13))

    def test_unrequested_are_unknown_not_negative_evidence(self):
        self.assertIn('"status": "unknown", "reason": "not_observed_in_bounded_refresh"',RUN)
        self.assertIn('insider_map.update(',RUN)
        self.assertIn('annotate_insiders, insider_refresh',RUN)
        self.assertIn('FINSCANNER_INSIDER_TICKER_BUDGET: "120"',WORKFLOW)


if __name__=="__main__":
    unittest.main()
