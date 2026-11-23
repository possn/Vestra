from pathlib import Path


def test_portfolio_hierarchy_uses_selector_array():
    js = Path("vestra-portfolio-hierarchy.js").read_text()
    # Regression guard: `for(const x of (a,b,c))` is a comma expression that
    # iterates a single string. Any for-of over a parenthesised list is a bug.
    import re
    assert not re.search(r"for\s*\(\s*const\s+\w+\s+of\s*\(\s*['\"]", js)


def test_portfolio_ui_text_helper_is_null_safe():
    js = Path("vestra-portfolio-ui.js").read_text()
    assert "function text(c,rx){ if(!c)return '';" in js


def test_portfolio_runtime_cache_busters_are_current():
    # These modules are no longer <script>-tagged in index.html; they are
    # fetched dynamically by market-static-universe.js's companion loader.
    # Assert the cache-buster lives there instead of a stale index.html check.
    loader = Path("market-static-universe.js").read_text()
    assert "vestra-portfolio-hierarchy.js?v=" in loader
    assert "vestra-portfolio-ui.js?v=" in loader
