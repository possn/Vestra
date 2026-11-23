import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.js").read_text(encoding="utf-8")
SW = (ROOT / "sw.js").read_text(encoding="utf-8")


def test_fluor_normalized_broker_ticker_can_recover_from_poisoned_baseline():
    assert '"FLR.US": Object.freeze({ ticker: "FLR", currency: "USD", minPrice: 10, maxPrice: 150 })' in APP
    assert '"FLR": Object.freeze({ ticker: "FLR", currency: "USD", minPrice: 10, maxPrice: 150 })' in APP


def test_view_render_is_deferred_by_one_frame_not_two():
    block = APP[APP.index("function setView(view)"):APP.index("function openModal(id)")]
    # Intent: a view switch waits for exactly one frame, never two nested ones.
    assert len(re.findall(r"=\s*requestAnimationFrame\(", block)) == 1
    assert not re.search(r"requestAnimationFrame\(\(\) => \{\s*pendingViewRenderFrame = null;\s*requestAnimationFrame", block)


def test_responsiveness_rollout_uses_fresh_service_worker_cache():
    assert re.search(r'const CACHE_NAME = "vestra-cache-v\d+";', SW)
    assert re.search(r"Service Worker v[\d.]+", SW)
