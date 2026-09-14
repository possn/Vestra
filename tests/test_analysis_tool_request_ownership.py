from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = (ROOT / "market-analysis-tools-runtime.js").read_text(encoding="utf-8")
LOADER = (ROOT / "market-static-universe.js").read_text(encoding="utf-8")


def _slice(start: str, end: str) -> str:
    after = RUNTIME.split(start, 1)[1]
    return after.split(end, 1)[0]


def test_analysis_tool_runtime_uses_request_generation_ownership():
    assert "let toolRequestGeneration = 0;" in RUNTIME
    assert "function ownsToolRequest(generation, tool, content)" in RUNTIME
    ownership = _slice("function ownsToolRequest", "function openSheet")
    assert "generation === toolRequestGeneration" in ownership
    assert "sheet.dataset.tool === tool" in ownership
    assert "content?.isConnected" in ownership
    assert "content === document.getElementById('marketSheetContent')" in ownership


def test_close_invalidates_pending_tool_work_before_mutating_sheet():
    close = _slice("function closeSheet()", "function header")
    assert "toolRequestGeneration += 1;" in close
    assert close.index("toolRequestGeneration += 1;") < close.index("sheet.hidden = true")


def test_open_tool_only_latest_request_can_open_or_render():
    open_tool = _slice("async function openTool(tool)", "function installStyles")
    assert "const generation = ++toolRequestGeneration;" in open_tool
    assert "await ensureMarket();" in open_tool
    assert "if (generation !== toolRequestGeneration) return;" in open_tool
    assert open_tool.index("if (generation !== toolRequestGeneration) return;") < open_tool.index("const content = openSheet(tool);")
    assert "await renderScanner(content, generation);" in open_tool


def test_scanner_rechecks_ownership_after_async_load():
    scanner = _slice("async function renderScanner(content, generation)", "function renderTheses")
    assert "const ok = await ensureScanner();" in scanner
    assert "if (!ownsToolRequest(generation, 'scanner', content)) return;" in scanner
    assert scanner.index("const ok = await ensureScanner();") < scanner.index("if (!ownsToolRequest(generation, 'scanner', content)) return;")
    assert scanner.index("if (!ownsToolRequest(generation, 'scanner', content)) return;") < scanner.index("if (!ok)")


def test_scanner_retry_starts_a_new_generation():
    handler = _slice("const retry = event.target.closest", "const open = event.target.closest")
    assert "const generation = ++toolRequestGeneration;" in handler
    assert "renderScanner(document.getElementById('marketSheetContent'), generation);" in handler


def test_loader_requests_owned_runtime_version():
    assert "market-analysis-tools-runtime.js?v=1.3" in LOADER
    assert "version:'1.3'" in RUNTIME
