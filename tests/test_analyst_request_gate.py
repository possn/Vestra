import importlib.util
from pathlib import Path
import sys
import threading
import time
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

MODULE_PATH = SCRIPTS / "run_market_pipeline.py"
spec = importlib.util.spec_from_file_location("run_market_pipeline_analyst_gate", MODULE_PATH)
runtime = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runtime
spec.loader.exec_module(runtime)


class AnalystRequestGateTests(unittest.TestCase):
    def test_gate_caps_simultaneous_endpoint_calls_at_three(self):
        active = 0
        peak = 0
        lock = threading.Lock()
        started = threading.Barrier(3)
        release = threading.Event()

        def original(fn):
            return fn()

        module = types.SimpleNamespace(_safe_call=original)
        runtime.install_analyst_request_gate(module, max_concurrent=3)

        def endpoint():
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            try:
                # The first three callers can enter together. Later callers must
                # wait on the semaphore until release is set.
                if active <= 3:
                    try:
                        started.wait(timeout=2)
                    except threading.BrokenBarrierError:
                        pass
                release.wait(timeout=2)
                return "ok"
            finally:
                with lock:
                    active -= 1

        results = []
        threads = [threading.Thread(target=lambda: results.append(module._safe_call(endpoint))) for _ in range(8)]
        for thread in threads:
            thread.start()
        started.wait(timeout=2)
        time.sleep(0.05)
        with lock:
            observed_peak = peak
        release.set()
        for thread in threads:
            thread.join(timeout=2)

        self.assertEqual(observed_peak, 3)
        self.assertEqual(peak, 3)
        self.assertEqual(results, ["ok"] * 8)
        self.assertEqual(module._analyst_request_gate_limit, 3)

    def test_gate_preserves_safe_call_return_and_exception_semantics(self):
        calls = []

        def original(fn):
            try:
                return fn()
            except Exception:
                return None

        module = types.SimpleNamespace(_safe_call=original)
        runtime.install_analyst_request_gate(module, max_concurrent=2)

        self.assertEqual(module._safe_call(lambda: calls.append("value") or 42), 42)
        self.assertIsNone(module._safe_call(lambda: (_ for _ in ()).throw(RuntimeError("boom"))))
        self.assertEqual(calls, ["value"])

    def test_reinstall_does_not_stack_existing_gate(self):
        call_count = 0

        def original(fn):
            nonlocal call_count
            call_count += 1
            return fn()

        module = types.SimpleNamespace(_safe_call=original)
        runtime.install_analyst_request_gate(module, max_concurrent=3)
        runtime.install_analyst_request_gate(module, max_concurrent=2)

        self.assertEqual(module._safe_call(lambda: "ok"), "ok")
        self.assertEqual(call_count, 1)
        self.assertEqual(module._analyst_request_gate_limit, 2)
        self.assertIs(module._vestra_original_safe_call, original)

    def test_limit_is_clamped_to_safe_range(self):
        module = types.SimpleNamespace(_safe_call=lambda fn: fn())
        runtime.install_analyst_request_gate(module, max_concurrent=0)
        self.assertEqual(module._analyst_request_gate_limit, 1)
        runtime.install_analyst_request_gate(module, max_concurrent=99)
        self.assertEqual(module._analyst_request_gate_limit, 8)


if __name__ == "__main__":
    unittest.main()
