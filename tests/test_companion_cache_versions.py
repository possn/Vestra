from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
LOADER = (ROOT / "market-static-universe.js").read_text(encoding="utf-8")

COMPANIONS = (
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


def declared_header_version(path: Path) -> str:
    head = path.read_text(encoding="utf-8")[:500]
    match = re.search(r"\bv(\d+\.\d+)\b", head, re.IGNORECASE)
    if not match:
        raise AssertionError(f"{path.name} has no declared header version")
    return match.group(1)


def loader_version(filename: str) -> str:
    pattern = rf"{re.escape(filename)}\?v=(\d+\.\d+)(?:[&'\"]|$)"
    match = re.search(pattern, LOADER)
    if not match:
        raise AssertionError(f"{filename} has no versioned loader URL")
    return match.group(1)


class CompanionCacheVersionTests(unittest.TestCase):
    def test_static_universe_companion_cache_versions_match_declared_versions(self):
        mismatches = []
        for filename in COMPANIONS:
            declared = declared_header_version(ROOT / filename)
            loaded = loader_version(filename)
            if declared != loaded:
                mismatches.append(f"{filename}: declared v{declared}, loader v{loaded}")
        self.assertEqual([], mismatches, "\n".join(mismatches))


if __name__ == "__main__":
    unittest.main(verbosity=2)
