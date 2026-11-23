from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEWS = (ROOT / "dashboard-daily-news.js").read_text(encoding="utf-8")
APP = (ROOT / "app.js").read_text(encoding="utf-8")
SW = (ROOT / "sw.js").read_text(encoding="utf-8")


def test_daily_news_observer_is_direct_child_only():
    assert "observer.observe(dashboard, { childList: true });" in NEWS
    assert "observer.observe(dashboard, { childList: true, subtree: true })" not in NEWS


def test_dashboard_navigation_uses_semantic_render_event_not_nav_click_probe():
    assert "vestra:view-rendered" in NEWS
    assert ".sidenavbtn[data-view=\"dashboard\"], .navbtn[data-view=\"dashboard\"]" not in NEWS


def test_rollout_cache_bumped():
    # Invariant (not a frozen version): the SW registration carries a cache-buster
    # and the worker declares a numbered cache generation.
    import re
    assert re.search(r'serviceWorker\.register\("sw\.js\?v=[\w.-]+"\)', APP)
    assert re.search(r'const CACHE_NAME = "vestra-cache-v\d+";', SW)
    assert re.search(r"Service Worker v[\d.]+", SW)
