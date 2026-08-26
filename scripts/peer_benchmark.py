"""Peer-first percentile benchmarking for Vestra score models.

This module is deliberately side-effect free. It does not change production scores
by itself. Score packs can migrate to it one component at a time after diagnostics
show that a global cross-sectional benchmark is economically inappropriate.

Policy:
- Prefer the economically coherent peer pool when it has enough observed values.
- Fall back to the wider/global pool when peers are too sparse.
- Missing values remain missing; they are never converted to zero.
- Return benchmark metadata so dossiers/audits can explain the comparison scope.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

DEFAULT_MIN_PEERS = 20


def _finite(value):
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def clean_values(values: Iterable) -> list[float]:
    return [x for x in (_finite(v) for v in values) if x is not None]


def percentile_rank(value, values: Iterable, *, invert: bool = False):
    x = _finite(value)
    clean = sorted(clean_values(values))
    if x is None or not clean:
        return None
    rank = sum(1 for v in clean if v <= x) / len(clean)
    pct = rank * 100.0
    return 100.0 - pct if invert else pct


@dataclass(frozen=True)
class BenchmarkResult:
    score: float | None
    scope: str
    peer_observations: int
    global_observations: int


def peer_first_percentile(
    value,
    peer_values: Iterable,
    global_values: Iterable,
    *,
    invert: bool = False,
    min_peers: int = DEFAULT_MIN_PEERS,
) -> BenchmarkResult:
    """Rank *value* against peers when the peer sample is sufficiently deep.

    `min_peers` refers to finite observed values, not nominal peer count. This is
    important for specialist metrics such as REIT FFO or bank provisions where a
    large sector can still have sparse usable observations.
    """
    peers = clean_values(peer_values)
    global_clean = clean_values(global_values)
    if len(peers) >= max(1, int(min_peers)):
        return BenchmarkResult(
            score=percentile_rank(value, peers, invert=invert),
            scope="peer_model",
            peer_observations=len(peers),
            global_observations=len(global_clean),
        )
    return BenchmarkResult(
        score=percentile_rank(value, global_clean, invert=invert),
        scope="global_fallback",
        peer_observations=len(peers),
        global_observations=len(global_clean),
    )


def benchmark_value(
    value,
    peers: Iterable,
    global_rows: Iterable,
    getter,
    *,
    invert: bool = False,
    min_peers: int = DEFAULT_MIN_PEERS,
) -> BenchmarkResult:
    """Convenience adapter for row/object collections."""
    return peer_first_percentile(
        value,
        (getter(x) for x in peers),
        (getter(x) for x in global_rows),
        invert=invert,
        min_peers=min_peers,
    )
