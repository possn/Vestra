from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LOADER = ROOT / "market-data-loader.js"


class MarketHydrationBadgeOwnershipTests(unittest.TestCase):
    def test_loading_generation_invalidates_older_removal_timeout(self):
        text = LOADER.read_text(encoding="utf-8")
        self.assertIn("badge.dataset.hydrationGeneration=String((Number(badge.dataset.hydrationGeneration)||0)+1)", text)
        self.assertIn("const generation=badge.dataset.hydrationGeneration||''", text)
        self.assertIn("badge.dataset.hydrationGeneration===generation", text)
        self.assertIn("badge.textContent===label", text)
        self.assertNotIn("if(badge?.isConnected) badge.remove()", text)

    def test_ready_and_partial_keep_existing_display_delays(self):
        text = LOADER.read_text(encoding="utf-8")
        self.assertIn("const label=state==='ready'?'✓ Dossier completo':'Detalhe parcial'", text)
        self.assertIn("const delay=state==='ready'?1400:1800", text)

    def test_only_latest_open_cycle_can_finish_dossier_hydration(self):
        text = LOADER.read_text(encoding="utf-8")
        self.assertIn("let dossierHydrationSeq = 0;", text)
        self.assertIn("const request=++dossierHydrationSeq;", text)
        self.assertIn("function ownsDossierHydration(request,ticker){", text)
        self.assertIn("return request===dossierHydrationSeq && !!dossierSheetFor(ticker);", text)
        self.assertGreaterEqual(text.count("if(!ownsDossierHydration(request,key))"), 2)

        success_guard = text.index("if(!ownsDossierHydration(request,key)) return stock;")
        refresh = text.index("refreshOpenDossier(key,stock);", success_guard)
        perf_delete = text.index("dossierOpenMarks.delete(key);", refresh)
        self.assertLess(success_guard, refresh)
        self.assertLess(refresh, perf_delete)

    def test_stale_hydration_failure_cannot_change_current_badge_or_perf_mark(self):
        text = LOADER.read_text(encoding="utf-8")
        catch_guard = text.index("if(!ownsDossierHydration(request,key)) return resolveIndexStock(key);")
        partial_badge = text.index("setHydrationBadge(key,'partial');", catch_guard)
        perf_delete = text.index("dossierOpenMarks.delete(key);", partial_badge)
        self.assertLess(catch_guard, partial_badge)
        self.assertLess(partial_badge, perf_delete)


if __name__ == "__main__":
    unittest.main(verbosity=2)
