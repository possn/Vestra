import importlib.util
from pathlib import Path
import sys
import threading
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

MODULE_PATH = SCRIPTS / "physical_metals_runtime.py"
spec = importlib.util.spec_from_file_location("physical_metals_runtime_test", MODULE_PATH)
runtime = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runtime
spec.loader.exec_module(runtime)


class PhysicalMetalsRuntimeTests(unittest.TestCase):
    def _module(self):
        barrier = threading.Barrier(6)
        seen = []
        lock = threading.Lock()

        def mark(name):
            with lock:
                seen.append(name)
            barrier.wait(timeout=2)
            return {"status": "ok", "name": name}

        module = types.SimpleNamespace()
        module._now = lambda: "2026-09-06T00:00:00Z"
        module.fetch_cme_stocks = lambda kind: mark(f"cme_{kind}")
        module.fetch_cme_delivery_notices = lambda: mark("deliveries")
        module.fetch_cftc_gold_positioning = lambda: mark("positioning")
        module.fetch_sge_benchmark = lambda: mark("shanghai")
        module.fetch_wgc_central_bank_changes = lambda: mark("central_banks")
        module.build_physical_payload = lambda: {"legacy": True}
        return module, seen

    def test_independent_adapters_run_concurrently_and_schema_is_preserved(self):
        module, seen = self._module()
        out = runtime.build_parallel(module=module, workers=6)

        self.assertEqual(set(seen), {
            "cme_gold", "cme_silver", "deliveries", "positioning", "shanghai", "central_banks"
        })
        self.assertEqual(out["generated_at"], "2026-09-06T00:00:00Z")
        self.assertEqual(out["comex"]["gold"]["name"], "cme_gold")
        self.assertEqual(out["comex"]["silver"]["name"], "cme_silver")
        self.assertEqual(out["deliveries"]["name"], "deliveries")
        self.assertEqual(out["positioning"]["gold"]["name"], "positioning")
        self.assertEqual(out["shanghai"]["gold_benchmark"]["name"], "shanghai")
        self.assertEqual(out["central_banks"]["name"], "central_banks")

    def test_install_replaces_only_payload_composition(self):
        module = types.SimpleNamespace(
            _now=lambda: "2026-09-06T00:00:00Z",
            fetch_cme_stocks=lambda kind: {"status": "ok", "kind": kind},
            fetch_cme_delivery_notices=lambda: {"status": "ok"},
            fetch_cftc_gold_positioning=lambda: {"status": "ok"},
            fetch_sge_benchmark=lambda: {"status": "ok"},
            fetch_wgc_central_bank_changes=lambda: {"status": "ok"},
            build_physical_payload=lambda: {"legacy": True},
        )
        original = module.build_physical_payload
        installed = runtime.install(module=module, workers=2)

        self.assertIs(module._vestra_original_build_physical_payload, original)
        self.assertIs(installed, module.build_physical_payload)
        out = module.build_physical_payload()
        self.assertEqual(out["comex"]["gold"]["kind"], "gold")
        self.assertEqual(out["comex"]["silver"]["kind"], "silver")


if __name__ == "__main__":
    unittest.main(verbosity=2)
