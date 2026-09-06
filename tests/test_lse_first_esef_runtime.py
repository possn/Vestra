import importlib.util
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

MODULE_PATH = SCRIPTS / "lse_first_esef_runtime.py"
spec = importlib.util.spec_from_file_location("lse_first_esef_runtime_test", MODULE_PATH)
runtime = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runtime
spec.loader.exec_module(runtime)


class LseFirstEsefRuntimeTests(unittest.TestCase):
    def _module(self, lse_result=None):
        calls = []

        def original(ticker, session=None):
            calls.append(("original", ticker))
            return "GB00YAHOO000", "Yahoo Finance"

        def lse(ticker, session=None):
            calls.append(("lse", ticker))
            return lse_result

        module = types.SimpleNamespace(
            resolve_isin_with_source=original,
            resolve_lse_isin=lse,
            ISIN_RE=__import__("re").compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$"),
        )
        return module, calls

    def test_london_ticker_uses_official_lse_before_yahoo(self):
        module, calls = self._module("GB00B0SWJX34")
        resolver = runtime.install(module)
        result = resolver("LSEG.L", session=object())

        self.assertEqual(result, ("GB00B0SWJX34", "London Stock Exchange official instrument API"))
        self.assertEqual(calls, [("lse", "LSEG.L")])

    def test_london_ticker_falls_back_to_existing_resolver_when_lse_misses(self):
        module, calls = self._module(None)
        resolver = runtime.install(module)
        result = resolver("LSEG.L", session=object())

        self.assertEqual(result, ("GB00YAHOO000", "Yahoo Finance"))
        self.assertEqual(calls, [("lse", "LSEG.L"), ("original", "LSEG.L")])

    def test_non_london_behavior_is_unchanged(self):
        module, calls = self._module("GB00B0SWJX34")
        resolver = runtime.install(module)
        result = resolver("AIR.PA", session=object())

        self.assertEqual(result, ("GB00YAHOO000", "Yahoo Finance"))
        self.assertEqual(calls, [("original", "AIR.PA")])


if __name__ == "__main__":
    unittest.main(verbosity=2)
