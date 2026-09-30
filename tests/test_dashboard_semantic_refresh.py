from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.js").read_text(encoding="utf-8")
UI = (ROOT / "dashboard-ui-refresh.js").read_text(encoding="utf-8")
NEWS = (ROOT / "dashboard-daily-news.js").read_text(encoding="utf-8")
SENTIMENT = (ROOT / "dashboard-market-sentiment.js").read_text(encoding="utf-8")
WEEKLY = (ROOT / "dashboard-weekly-events.js").read_text(encoding="utf-8")
SW = (ROOT / "sw.js").read_text(encoding="utf-8")


def test_dashboard_brief_uses_semantic_events_not_whole_dashboard_mutation_observer():
    assert "todayObserver" not in UI
    assert "todayObserver.observe(dashboard" not in UI
    assert "vestra:dashboard-signal-updated" in UI
    assert "setTimeout(refresh, 60)" not in UI


def test_async_dashboard_sources_emit_semantic_signal_event():
    assert "source: 'daily-news'" in NEWS
    assert "source: 'market-sentiment'" in SENTIMENT
    assert "source: 'weekly-events'" in WEEKLY


def test_navigation_emits_post_render_event():
    block = APP[APP.index("function setView(view)"):APP.index("function openModal(id)")]
    assert 'new CustomEvent("vestra:view-rendered"' in block
    assert 'renderView(view, { force: false, sync: true });' in block


def test_rollout_cache_is_fresh():
    assert 'sw.js?v=20260930v4' in APP
    assert 'const CACHE_NAME = "vestra-cache-v236";' in SW
    assert "Service Worker v11.14" in SW
