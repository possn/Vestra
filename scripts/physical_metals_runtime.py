"""Runtime composition for independent physical-metals network adapters.

The physical evidence sources do not depend on one another. Running them in
sequence turns several unrelated 25-30s network timeouts into cumulative wall
clock delay. This wrapper preserves the exact payload schema while executing the
independent adapters with a small bounded pool.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed


def build_parallel(module=None, workers=5):
    if module is None:
        import physical_metals as module

    jobs = {
        "comex_gold": lambda: module.fetch_cme_stocks("gold"),
        "comex_silver": lambda: module.fetch_cme_stocks("silver"),
        "deliveries": module.fetch_cme_delivery_notices,
        "positioning_gold": module.fetch_cftc_gold_positioning,
        "shanghai_gold": module.fetch_sge_benchmark,
        "central_banks": module.fetch_wgc_central_bank_changes,
    }
    results = {}
    with ThreadPoolExecutor(max_workers=max(1, min(int(workers), len(jobs)))) as pool:
        futures = {pool.submit(fn): key for key, fn in jobs.items()}
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception as exc:
                # Individual adapters normally fail closed themselves. Preserve
                # that contract even if one unexpectedly escapes its boundary.
                results[key] = {"status": "unavailable", "error": f"{type(exc).__name__}: {exc}"[:240]}

    return {
        "generated_at": module._now(),
        "comex": {
            "gold": results.get("comex_gold", {"status": "unavailable"}),
            "silver": results.get("comex_silver", {"status": "unavailable"}),
        },
        "deliveries": results.get("deliveries", {"status": "unavailable"}),
        "positioning": {"gold": results.get("positioning_gold", {"status": "unavailable"})},
        "shanghai": {"gold_benchmark": results.get("shanghai_gold", {"status": "unavailable"})},
        "central_banks": results.get("central_banks", {"status": "unavailable"}),
    }


def install(module=None, workers=5):
    if module is None:
        import physical_metals as module
    if getattr(module, "_vestra_parallel_physical_metals_installed", False):
        return module.build_physical_payload

    original = module.build_physical_payload

    def parallel_payload():
        return build_parallel(module=module, workers=workers)

    module._vestra_original_build_physical_payload = original
    module.build_physical_payload = parallel_payload
    module._vestra_parallel_physical_metals_installed = True
    return parallel_payload
