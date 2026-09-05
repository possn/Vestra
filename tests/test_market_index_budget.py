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
    assert m.MAX_INDEX_BYTES == 7_250_000
    assert m.MAX_INDEX_RATIO == 0.15


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


def test_published_index_is_inside_new_budget():
    m = load_builder()
    index_size = (ROOT / "data" / "stocks-index.json").stat().st_size
    source_size = (ROOT / "data" / "stocks.json").stat().st_size
    assert index_size <= m.MAX_INDEX_BYTES
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
