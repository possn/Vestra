"""Refresh the compact Dashboard news feed without running the full market pipeline."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from news import _build_dashboard_digest

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "dashboard-news.json"


def main() -> int:
    payload = _build_dashboard_digest({})
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list) or not items:
        raise RuntimeError("dashboard news refresh returned no items")
    generated = payload.get("generated_at")
    if not generated:
        payload["generated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"generated_at": payload["generated_at"], "items": len(items)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
