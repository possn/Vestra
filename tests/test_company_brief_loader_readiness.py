from pathlib import Path


SRC = Path('market-company-brief.js').read_text(encoding='utf-8')


def _loader_source():
    start = SRC.index('function loadScript(')
    end = SRC.index('\nfunction loadResearchDiagnostics', start)
    return SRC[start:end]


def test_existing_script_waits_for_load_before_callback():
    loader = _loader_source()
    assert "const existing=document.getElementById(id)" in loader
    assert "if(existing){if(onload)existing.addEventListener('load',onload,{once:true});return;}" in loader
    assert "ready||document.getElementById(id)" not in loader


def test_ready_dependency_may_run_callback_immediately():
    loader = _loader_source()
    assert "if(ready){if(onload)onload();return;}" in loader
    assert loader.index("if(ready)") < loader.index("const existing=document.getElementById(id)")


def test_new_script_keeps_load_callback_contract():
    loader = _loader_source()
    assert "const s=document.createElement('script')" in loader
    assert "if(onload)s.addEventListener('load',onload,{once:true})" in loader
    assert "document.head.appendChild(s)" in loader
