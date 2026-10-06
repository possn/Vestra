from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_market_shards.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("vestra_build_market_shards", BUILDER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_market_index_has_explicit_mobile_budget():
    m = load_builder()
    assert m.MAX_INDEX_BYTES == 7_500_000
    assert m.MAX_INDEX_HARD_BYTES == 9_000_000
    assert m.MAX_INDEX_BYTES < m.MAX_INDEX_HARD_BYTES
    assert m.MAX_INDEX_RATIO == 0.15


def test_legacy_index_soft_overage_does_not_block_compact_market_publish():
    source = BUILDER.read_text(encoding="utf-8")
    assert "if idx_size > MAX_INDEX_HARD_BYTES:" in source
    assert "if idx_size > MAX_INDEX_BYTES:" in source
    advisory = source.split("if idx_size > MAX_INDEX_BYTES:", 1)[1].split("if src_size > 0", 1)[0]
    assert "WARNING: legacy market index exceeds advisory budget" in advisory
    assert "raise RuntimeError" not in advisory


def test_detail_only_thesis_copy_does_not_enter_startup_row():
    m = load_builder()
    row = {
        "ticker": "TEST",
        "name": "Test Corp",
        "score": 75,
        "thesis_type": "Quality Growth",
        "thesis_direction": "up",
        "thesis_slug": "quality-growth",
        "thesis_summary": "Long human-readable thesis copy that belongs in the dossier.",
    }
    compact = m.index_row(row)
    assert compact["ticker"] == "TEST"
    assert compact["name"] == "Test Corp"
    assert compact["score"] == 75
    assert compact["thesis_type"] == "Quality Growth"
    assert compact["thesis_direction"] == "up"
    assert "thesis_slug" not in compact
    assert "thesis_summary" not in compact


def test_compact_rotation_returns_use_observed_daily_scalars_without_shipping_history():
    m = load_builder()
    row = {
        "ticker": "TEST",
        "quote_type": "EQUITY",
        "price_history_1y": [{"close": float(x)} for x in range(100, 126)],
        "market_return_5d_pct": 4.1667,
        "market_return_20d_pct": 19.0476,
    }
    compact = m.index_row(row)
    assert compact["market_return_5d_pct"] == 4.1667
    assert compact["market_return_20d_pct"] == 19.0476
    assert "price_history_1y" not in compact

    no_daily = m.index_row({
        "ticker": "NODAILY",
        "quote_type": "EQUITY",
        "price_history_1y": [{"close": float(x)} for x in range(100, 126)],
    })
    assert "market_return_5d_pct" not in no_daily
    assert "market_return_20d_pct" not in no_daily


def test_published_index_respects_hard_budget_and_relative_budget():
    m = load_builder()
    index_size = (ROOT / "data" / "stocks-index.json").stat().st_size
    source_size = (ROOT / "data" / "stocks.json").stat().st_size
    # MAX_INDEX_BYTES is advisory by contract; only the hard absolute ceiling
    # and relative payload budget are publication blockers.
    assert index_size <= m.MAX_INDEX_HARD_BYTES
    assert index_size / source_size <= m.MAX_INDEX_RATIO


def test_columnar_encoding_is_materially_smaller_and_value_equivalent():
    m = load_builder()
    payload = json.loads((ROOT / "data" / "stocks-index.json").read_text(encoding="utf-8"))
    packed = m.pack_index_payload(payload)
    decoded = m.unpack_index_payload(packed)

    original_bytes = len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    packed_bytes = len(json.dumps(packed, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    saving_ratio = 1 - packed_bytes / original_bytes
    assert saving_ratio >= m.MIN_COLUMNAR_SAVING_RATIO

    assert decoded["schema_version"] == payload["schema_version"]
    assert decoded["generated_at"] == payload["generated_at"]
    assert len(decoded["stocks"]) == len(payload["stocks"])

    keys = (
        "ticker", "name", "score", "current_price", "currency", "quote_type",
        "opportunity_score", "low52_status", "recovery_score", "dossier_shard",
    )
    for original, rebuilt in zip(payload["stocks"][:50], decoded["stocks"][:50]):
        for key in keys:
            assert rebuilt.get(key) == original.get(key)
