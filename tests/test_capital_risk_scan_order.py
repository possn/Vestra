from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import capital_risk_scan_order


class FakeModule:
    def __init__(self):
        self.received = None

    def _scan_docs(self, client, cik, rows, max_docs=8):
        self.received = list(rows)
        return {"rows": list(rows), "max_docs": max_docs}


class CapitalRiskScanOrderTests(unittest.TestCase):
    def test_form_priority_is_preserved_and_recency_is_descending_inside_class(self):
        rows = [
            {"form": "8-K", "date": "2025-01-01", "accession": "old-8k"},
            {"form": "10-K", "date": "2026-08-01", "accession": "new-10k"},
            {"form": "8-K", "date": "2026-09-01", "accession": "new-8k"},
            {"form": "424B5", "date": "2026-07-01", "accession": "424"},
        ]
        selected = capital_risk_scan_order.select_recent_priority(rows, max_docs=4)
        self.assertEqual(
            [row["accession"] for row in selected],
            ["new-8k", "old-8k", "424", "new-10k"],
        )

    def test_bounded_selection_cannot_evict_newer_same_class_filing(self):
        rows = [
            {"form": "8-K", "date": f"2026-08-{day:02d}", "accession": f"a{day:02d}"}
            for day in range(1, 11)
        ]
        selected = capital_risk_scan_order.select_recent_priority(rows, max_docs=8)
        self.assertEqual([row["accession"] for row in selected], [f"a{day:02d}" for day in range(10, 2, -1)])
        self.assertNotIn("a01", {row["accession"] for row in selected})
        self.assertNotIn("a02", {row["accession"] for row in selected})

    def test_wrapper_passes_only_selected_subset_to_canonical_scanner(self):
        module = FakeModule()
        wrapped = capital_risk_scan_order.install(module=module)
        rows = [
            {"form": "8-K", "date": f"2026-08-{day:02d}", "accession": f"a{day:02d}"}
            for day in range(1, 11)
        ]
        result = wrapped(None, 1, rows, max_docs=3)
        self.assertEqual([row["accession"] for row in module.received], ["a10", "a09", "a08"])
        self.assertEqual(result["max_docs"], 3)

    def test_install_is_idempotent(self):
        module = FakeModule()
        first = capital_risk_scan_order.install(module=module)
        second = capital_risk_scan_order.install(module=module)
        self.assertIs(first, second)


if __name__ == "__main__":
    unittest.main(verbosity=2)
