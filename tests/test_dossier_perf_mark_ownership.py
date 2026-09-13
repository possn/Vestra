import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DossierPerfMarkOwnershipTests(unittest.TestCase):
    def test_stale_hydration_cannot_release_newer_open_mark(self):
        source = (ROOT / "market-data-loader.js").read_text(encoding="utf-8")

        self.assertIn(
            "if(dossierOpenMarks.get(key)!==mark || mark.sheetMs!=null) return;",
            source,
            "requestAnimationFrame must only write timing to the mark created by that open cycle",
        )
        self.assertIn(
            "if(key && mark && dossierOpenMarks.get(key)===mark) dossierOpenMarks.delete(key);",
            source,
            "mark cleanup must use object identity so an old hydration cannot delete a newer mark",
        )
        self.assertIn(
            "const openMark=dossierOpenMarks.get(key)||null;",
            source,
            "hydrateOpenDossier must capture the opening mark before asynchronous hydration",
        )
        self.assertGreaterEqual(
            source.count("releaseDossierOpenMark(key,openMark);"),
            4,
            "both stale and owned success/failure paths must release only their captured mark",
        )
        self.assertNotIn(
            "dossierOpenMarks.delete(key);\n      return stock;",
            source,
            "hydration completion must not delete a mark without ownership validation",
        )


if __name__ == "__main__":
    unittest.main()
