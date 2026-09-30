from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.js").read_text(encoding="utf-8")
CONC = (ROOT / "dashboard-portfolio-concentration.js").read_text(encoding="utf-8")
SW = (ROOT / "sw.js").read_text(encoding="utf-8")


def test_scheduled_renders_publish_semantic_view_completion():
    block = APP[APP.index("function scheduleRenderView"):APP.index('window.addEventListener("vestra:charts-ready"')]
    assert 'new CustomEvent("vestra:view-rendered"' in block


def test_portfolio_mode_change_is_semantic_not_click_timeout_driven():
    block = APP[APP.index("function setModeLiabs"):APP.index("function rebuildClassFilter")]
    assert 'new CustomEvent("vestra:portfolio-mode-changed"' in block
    assert "setTimeout" not in block


def test_concentration_has_no_kpi_dom_observer_or_navigation_delay():
    assert "new MutationObserver" not in CONC
    assert "getElementById('kpiNet')" not in CONC
    assert "setTimeout(()=>{render();scheduleLookthrough();},60)" not in CONC
    assert "vestra:view-rendered" in CONC
    assert "vestra:portfolio-mode-changed" in CONC


def test_rollout_cache_bumped():
    assert 'sw.js?v=20260930v6' in APP
    assert 'const CACHE_NAME = "vestra-cache-v238";' in SW
    assert "Service Worker v11.16" in SW
