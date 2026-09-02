"""Seed the SEC ticker/CIK snapshot from a cryptographically pinned transport.

GitHub-hosted runners can be blocked by www.sec.gov's WAF even though the SEC
catalogue itself is public. The canonical SEC enricher remains remote-first and
unchanged; this helper only ensures that its existing validated snapshot fallback
exists before the pipeline starts.

The transport below is pinned to an immutable GitHub commit and is accepted only
when the raw bytes match the SHA-256 published in that commit's reference-data
manifest, the official SEC exchange schema has the expected row count, and
well-known ticker/CIK sentinels match. The snapshot's `source` remains the
official SEC URL: the GitHub repository is transport/cache, not provenance.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

import requests

from sec_enrich import (
    TICKERS_EXCHANGE,
    TICKER_MAP_SCHEMA_VERSION,
    TICKER_MAP_SNAPSHOT,
    _parse_company_tickers_exchange,
    _read_ticker_snapshot,
    _validated_map,
)

MIRROR_REPOSITORY = "VlKAS/open-tax-ledger"
MIRROR_COMMIT = "613c946973fb3cab27ecee35905eb5d91731f8e0"
MIRROR_PATH = "reference-data/sec-company-tickers-exchange.json"
MIRROR_URL = (
    f"https://raw.githubusercontent.com/{MIRROR_REPOSITORY}/{MIRROR_COMMIT}/{MIRROR_PATH}"
)
EXPECTED_SHA256 = "e6fbad74d63540e73239f257809cf217b9d6b4fed2410691f0c8c576c9a6cf3c"
EXPECTED_FIELDS = ["cik", "name", "ticker", "exchange"]
EXPECTED_RECORDS = 10432
EXPECTED_SENTINELS = {
    "AAPL": 320193,
    "MSFT": 789019,
    "NVDA": 1045810,
}
UPSTREAM_LAST_MODIFIED = "2026-07-24T13:32:36.000Z"


def _verified_mapping(raw: bytes):
    if not isinstance(raw, (bytes, bytearray)) or not raw:
        raise ValueError("empty SEC ticker-map transport payload")

    digest = hashlib.sha256(bytes(raw)).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError(f"SEC ticker-map transport checksum mismatch: {digest}")

    try:
        payload = json.loads(bytes(raw).decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"SEC ticker-map transport is not valid UTF-8 JSON: {exc}") from exc

    if payload.get("fields") != EXPECTED_FIELDS:
        raise ValueError(f"unexpected SEC ticker-map fields: {payload.get('fields')!r}")
    rows = payload.get("data")
    if not isinstance(rows, list) or len(rows) != EXPECTED_RECORDS:
        raise ValueError(
            f"unexpected SEC ticker-map row count: {len(rows) if isinstance(rows, list) else 'invalid'}"
        )

    mapping = _validated_map(_parse_company_tickers_exchange(payload))
    if not mapping or len(mapping) < 10_000:
        raise ValueError("SEC ticker-map transport produced too few exact ticker/CIK mappings")
    for ticker, cik in EXPECTED_SENTINELS.items():
        if mapping.get(ticker) != cik:
            raise ValueError(
                f"SEC ticker-map sentinel mismatch for {ticker}: {mapping.get(ticker)!r} != {cik}"
            )
    return mapping, digest


def _write_seed_snapshot(mapping, digest, path=TICKER_MAP_SNAPSHOT):
    mapping = _validated_map(mapping)
    if not mapping:
        raise ValueError("invalid SEC ticker map")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TICKER_MAP_SCHEMA_VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": TICKERS_EXCHANGE,
        "count": len(mapping),
        "map": dict(sorted(mapping.items())),
        "transport": "pinned_github_mirror",
        "transport_repository": MIRROR_REPOSITORY,
        "transport_commit": MIRROR_COMMIT,
        "transport_path": MIRROR_PATH,
        "upstream_sha256": digest,
        "upstream_last_modified": UPSTREAM_LAST_MODIFIED,
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return payload


def seed_snapshot(session=None, path=TICKER_MAP_SNAPSHOT):
    """Create a verified fallback only when no valid snapshot already exists."""
    existing = _read_ticker_snapshot(path)
    if existing:
        mapping, payload = existing
        print(
            "SEC ticker-map seed: existing validated snapshot kept "
            f"({len(mapping)} tickers, source={payload.get('source') or 'unknown'})"
        )
        return mapping, payload, False

    session = session or requests.Session()
    response = session.get(MIRROR_URL, timeout=30)
    if not getattr(response, "ok", False):
        raise RuntimeError(
            f"SEC ticker-map pinned transport failed: HTTP {getattr(response, 'status_code', 'unknown')}"
        )
    raw = getattr(response, "content", None)
    mapping, digest = _verified_mapping(raw)
    payload = _write_seed_snapshot(mapping, digest, path)
    print(
        "SEC ticker-map seed: verified pinned transport accepted "
        f"({len(mapping)} exact tickers; sha256={digest}) -> {path}"
    )
    return mapping, payload, True


def main():
    seed_snapshot()


if __name__ == "__main__":
    main()
