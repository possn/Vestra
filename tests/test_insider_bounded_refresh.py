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


def load_invalidator():
    tree=ast.parse(RUN)
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
            and n.name=="_invalidate_carried_insider_evidence")
    ns={}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),"run.py","exec"),ns)
    return ns["_invalidate_carried_insider_evidence"]


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

    def test_carried_forward_transaction_counts_never_masquerade_as_current(self):
        invalidate=load_invalidator()
        old={"insider_status":"ok", "insider_buy_count_30d":30,
             "insider_buy_value_30d":402700000,"insider_transactions":[{"date":"2026-09-30"}],
             "insider_net_value_30d":402700000,
             "thesis_summary":"Insider purchases support accumulation",
             "thesis_type":"Insider Accumulation", "thesis_slug":"insider-accumulation",
             "thesis_evidence":["Fluxo de insiders em 30 dias", "Cash flow saudável"],
             "catalyst_events":[{"kind":"insiders","label":"30 compras"},
                                {"kind":"earnings","label":"Resultados"}],
             "scanner_results":{"insider_accumulation":{"score":80},"other":{"score":65}}}
        fresh=invalidate(dict(old))
        self.assertEqual(fresh["insider_status"],"unknown")
        self.assertIsNone(fresh["insider_buy_count_30d"])
        self.assertIsNone(fresh["insider_buy_value_30d"])
        self.assertEqual(fresh["insider_transactions"],[])
        self.assertEqual(fresh["catalyst_events"],[{"kind":"earnings","label":"Resultados"}])
        self.assertEqual(fresh["thesis_evidence"],["Cash flow saudável"])
        self.assertIsNone(fresh["thesis_summary"])
        self.assertIsNone(fresh["thesis_type"])
        self.assertEqual(list(fresh["scanner_results"]),["other"])
        self.assertIn("insider_accumulation",old["scanner_results"],"do not mutate source row")


if __name__=="__main__":
    unittest.main()
