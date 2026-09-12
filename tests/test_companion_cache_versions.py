from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]

STATIC_UNIVERSE_LOADER = (ROOT / "market-static-universe.js").read_text(encoding="utf-8")
COMPANY_BRIEF_LOADER = (ROOT / "market-company-brief.js").read_text(encoding="utf-8")
UI_POLISH_LOADER = (ROOT / "market-ui-polish.js").read_text(encoding="utf-8")

STATIC_UNIVERSE_COMPANIONS = (
    "market-etf-intelligence.js",
    "market-scanner-data.js",
    "market-analysis-tools-runtime.js",
    "dashboard-weekly-events.js",
    "dashboard-weekly-events-navigation.js",
    "dashboard-ui-refresh.js",
    "mobile-ui-refresh.js",
    "market-ui-polish.js",
    "ui-visual-polish.js",
)

COMPANY_BRIEF_COMPANIONS = (
    "quote-canonical-repair.js",
    "market-dossier-controls.js",
    "market-global-search.js",
    "market-learned-universe.js",
    "app-update-manager.js",
    "market-data-health.js",
    "app-runtime-bridge.js",
)

UI_POLISH_COMPANIONS = (
    "market-stock-themes-tools.js",
)


def declared_header_version(path: Path) -> str:
    head = path.read_text(encoding="utf-8")[:500]
    match = re.search(r"\bv(\d+\.\d+)\b", head, re.IGNORECASE)
    if not match:
        raise AssertionError(f"{path.name} has no declared header version")
    return match.group(1)


def loader_version(loader: str, filename: str) -> str:
    pattern = rf"{re.escape(filename)}\?v=(\d+\.\d+)(?:[&'\"]|$)"
    match = re.search(pattern, loader)
    if not match:
        raise AssertionError(f"{filename} has no versioned loader URL")
    return match.group(1)


def mismatches_for(loader: str, filenames: tuple[str, ...]) -> list[str]:
    mismatches = []
    for filename in filenames:
        declared = declared_header_version(ROOT / filename)
        loaded = loader_version(loader, filename)
        if declared != loaded:
            mismatches.append(f"{filename}: declared v{declared}, loader v{loaded}")
    return mismatches


class CompanionCacheVersionTests(unittest.TestCase):
    def test_static_universe_companion_cache_versions_match_declared_versions(self):
        self.assertEqual(
            [],
            mismatches_for(STATIC_UNIVERSE_LOADER, STATIC_UNIVERSE_COMPANIONS),
        )

    def test_company_brief_companion_cache_versions_match_declared_versions(self):
        self.assertEqual(
            [],
            mismatches_for(COMPANY_BRIEF_LOADER, COMPANY_BRIEF_COMPANIONS),
        )

    def test_ui_polish_companion_cache_versions_match_declared_versions(self):
        self.assertEqual(
            [],
            mismatches_for(UI_POLISH_LOADER, UI_POLISH_COMPANIONS),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
