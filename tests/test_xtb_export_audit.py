"""Synthetic XLSX tests for the offline XTB export audit."""
import importlib.util
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

spec = importlib.util.spec_from_file_location("xtb_audit", Path(__file__).resolve().parents[1] / "scripts/audit_xtb_exports.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def sheet_xml(rows):
    root = ET.Element(f"{{{NS}}}worksheet")
    data = ET.SubElement(root, f"{{{NS}}}sheetData")
    for index, row in enumerate(rows, 1):
        node = ET.SubElement(data, f"{{{NS}}}row", r=str(index))
        for column, value in row.items():
            cell = ET.SubElement(node, f"{{{NS}}}c", r=f"{column}{index}", t="inlineStr")
            inline = ET.SubElement(cell, f"{{{NS}}}is")
            ET.SubElement(inline, f"{{{NS}}}t").text = str(value)
    return ET.tostring(root, encoding="utf-8")


class XtbAuditTests(unittest.TestCase):
    def build(self, path, duplicate=False):
        cash = [
            {"A": "Cash Operations"},
            {"A": "Type", "F": "Amount", "G": "ID"},
            {"A": "Dividend", "F": "1.25", "G": "100"},
            {"A": "Withholding tax", "F": "-0.25", "G": "100" if duplicate else "101"},
        ]
        positions = [
            {"A": "Open Positions"},
            {"A": "Product", "B": "Metric", "C": "Amount"},
            {"A": "My Trades", "B": "Value", "C": "90.25"},
            {"A": "Investment Plans", "B": "Value", "C": "9.75"},
        ]
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("xl/worksheets/sheet2.xml", sheet_xml(cash))
            archive.writestr("xl/worksheets/sheet3.xml", sheet_xml(positions))

    def test_totals_and_distinct_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "synthetic.xlsx"
            self.build(path)
            result = module.audit(path)
            self.assertEqual(result["cash_operations"], 2)
            self.assertEqual(result["cash_totals_by_type_eur"]["Withholding tax"], "-0.25")
            self.assertEqual(result["total_reported_open_position_value_eur"], "100.00")
            self.assertTrue(result["identity_check_passed"])

    def test_duplicate_ids_flagged(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "synthetic.xlsx"
            self.build(path, duplicate=True)
            self.assertEqual(module.audit(path)["duplicate_cash_operation_ids"], 1)


if __name__ == "__main__":
    unittest.main()
