from pathlib import Path


SRC = Path('market-company-brief.js').read_text(encoding='utf-8')


def _loader_source():
    start = SRC.index('function loadScript(')
    end = SRC.index('\nfunction loadResearchDiagnostics', start)
    return SRC[start:end]


def test_existing_script_is_observed_before_retry_or_callback():
    loader = _loader_source()
    assert "const existing=document.getElementById(id)" in loader
    assert "const s=existing||document.createElement('script')" in loader
    assert "s.addEventListener('load',onLoad,{once:true})" in loader
    assert "s.addEventListener('error',onError,{once:true})" in loader
    assert "if(s.isConnected)s.remove()" in loader


def test_ready_dependency_may_run_callback_immediately_and_is_rechecked():
    loader = _loader_source()
    assert "const isReady=()=>typeof ready==='function'?!!ready():!!ready;" in loader
    assert "if(isReady()){if(onload)onload();return;}" in loader
    assert "if(!isReady()){fail();return;}" in loader
    assert loader.index("if(isReady())") < loader.index("const existing=document.getElementById(id)")


def test_new_script_keeps_load_callback_contract_with_deadline():
    loader = _loader_source()
    assert "const s=existing||document.createElement('script')" in loader
    assert "timeoutId=setTimeout(fail,SCRIPT_LOAD_TIMEOUT_MS)" in loader
    assert "if(onload)onload();" in loader
    assert "if(!existing){s.id=id;s.src=src;s.defer=true;document.head.appendChild(s)}" in loader
