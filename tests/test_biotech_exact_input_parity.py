import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from types import ModuleType
from unittest.mock import patch

fundamentals_stub = ModuleType("fundamentals")
fundamentals_stub.RawMetrics = type("RawMetrics", (), {})
with patch.dict(sys.modules, {"fundamentals": fundamentals_stub}):
    from score import _avg, _percentile_rank, _benchmark_values

class BiotechNativeQualityParity(unittest.TestCase):
    def test_native_peer_rank_reconstruction(self):
        gross = [0.11, 0.20, 0.40, 0.50, 0.60]
        roa = [-0.6, -0.3, 0.0, 0.05, 0.1]
        native = _avg([_percentile_rank(0.4, gross), _percentile_rank(0.0, roa)])
        self.assertAlmostEqual(native, 60.0)
        self.assertAlmostEqual(_avg([None, _percentile_rank(0.0, roa)]), 60.0)

    def test_peer_global_fallback_contract(self):
        peers = [0.1] * 19
        global_pool = [0.2] * 24
        self.assertEqual(_benchmark_values(peers, global_pool), global_pool)
        self.assertEqual(_benchmark_values(peers + [0.1], global_pool), peers + [0.1])

if __name__ == "__main__":
    unittest.main()
