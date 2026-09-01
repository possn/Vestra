from pathlib import Path


def test_portfolio_hierarchy_uses_selector_array():
    js = Path("vestra-portfolio-hierarchy.js").read_text()
    assert "for(const sel of ['.ux454-nav-title','.market-collapse-toolbar','.ux453-focusbar','.ux-portfolio-shortcuts'])" in js
    assert "for(const sel of ('.ux454-nav-title','.market-collapse-toolbar','.ux453-focusbar','.ux-portfolio-shortcuts'))" not in js


def test_portfolio_ui_text_helper_is_null_safe():
    js = Path("vestra-portfolio-ui.js").read_text()
    assert "function text(c,rx){ if(!c)return '';" in js


def test_portfolio_runtime_cache_busters_are_current():
    html = Path("index.html").read_text()
    assert "vestra-portfolio-hierarchy.js?v=1.3" in html
    assert "vestra-portfolio-ui.js?v=1.1" in html
