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


class InsiderCacheLowerBoundTests(unittest.TestCase):
    def _cache(self):
        def tx(day, side, value, cik="0000000123"):
            return {"date": day, "type": side, "value": value, "issuer_cik": cik}
        return {
            "123:a": {"issuer_cik": "0000000123", "filing_date": "2026-11-15",
                      "transactions": [tx("2026-11-12", "buy", 1000.0), tx("2026-11-12", "sell", 400.0)]},
            "123:b": {"issuer_cik": "0000000123", "filing_date": "2026-08-01",
                      "transactions": [tx("2026-07-30", "buy", 5000.0)]},
            "999:c": {"issuer_cik": "0000000999", "filing_date": "2026-11-15",
                      "transactions": [tx("2026-11-14", "buy", 9e9, cik="0000000999")]},
        }

    def _load(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import insiders
        return insiders

    def test_partial_lower_bound_windows_and_issuer_isolation(self):
        ins = self._load()
        out = ins.insider_from_cache("AAA", cik_map={"AAA": "0000000123"},
                                     asof=date(2026, 11, 23), cache=self._cache())
        self.assertEqual(out["status"], "partial")
        self.assertEqual((out["buy_count_30d"], out["sell_count_30d"]), (1, 1))
        self.assertEqual(out["buy_value_30d"], 1000.0)          # other issuer excluded
        self.assertEqual(out["buy_count_365d"], 2)
        self.assertEqual(out["buy_value_365d"], 6000.0)
        self.assertIsNone(out["net_value_30d"])                # never a net on incomplete data
        self.assertIsNone(out["net_value_365d"])

    def test_old_trades_leave_30d_window_but_stay_in_365d(self):
        ins = self._load()
        out = ins.insider_from_cache("AAA", cik_map={"AAA": "0000000123"},
                                     asof=date(2026, 12, 20), cache=self._cache())
        self.assertEqual(out["buy_count_30d"], 0)
        self.assertEqual(out["buy_count_365d"], 2)

    def test_no_cached_trades_or_non_us_is_none_never_zero(self):
        ins = self._load()
        self.assertIsNone(ins.insider_from_cache("ZZZ", cik_map={"ZZZ": "0000000555"},
                                                 asof=date(2026, 11, 23), cache=self._cache()))
        self.assertIsNone(ins.insider_from_cache("ABC.L", cik_map={"ABC.L": "0000000123"},
                                                 asof=date(2026, 11, 23), cache=self._cache()))
        self.assertIsNone(ins.insider_from_cache("AAA", cik_map={}, cache=self._cache()))

    def test_run_wires_cache_fallback_before_unknown(self):
        self.assertIn("insider_from_cache(ticker, cik_map=_cik_map)", RUN)
        self.assertIn('"status": "unknown", "reason": "not_observed_in_bounded_refresh"', RUN)


class InsiderPartialUiGuardTests(unittest.TestCase):
    def test_dossier_never_nets_a_verified_lower_bound(self):
        market = (ROOT / "market.js").read_text(encoding="utf-8")
        self.assertIn("const lowerBound=txt(s.insider_status)==='partial';", market)
        self.assertIn("? null\n      : hasCompleteValue", market)
        self.assertIn("Mínimo verificado: ", market)
