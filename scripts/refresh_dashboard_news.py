"""Refresh the compact Dashboard news feed without running the full market pipeline."""
from __future__ import annotations

import email.utils
import json
from datetime import datetime, timezone
from pathlib import Path

from news import _build_dashboard_digest

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "dashboard-news.json"
MAX_ITEMS = 40
COMPANY_RETENTION_HOURS = 36


def published_ts(value: str) -> float:
    try:
        dt = email.utils.parsedate_to_datetime(value or "")
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0.0


def previous_company_items(now_ts: float) -> list[dict]:
    try:
        previous = json.loads(OUTPUT.read_text(encoding="utf-8"))
    except Exception:
        return []
    rows = previous.get("items") if isinstance(previous, dict) else []
    kept = []
    for item in rows if isinstance(rows, list) else []:
        if item.get("kind") != "company":
            continue
        ts = published_ts(str(item.get("published") or ""))
        if not ts:
            continue
        age_hours = max(0.0, (now_ts - ts) / 3600.0)
        if age_hours <= COMPANY_RETENTION_HOURS:
            kept.append(item)
    return kept


def main() -> int:
    payload = _build_dashboard_digest({})
    fresh = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(fresh, list) or not fresh:
        raise RuntimeError("dashboard news refresh returned no market items")

    now = datetime.now(timezone.utc)
    combined = []
    seen = set()
    for item in [*previous_company_items(now.timestamp()), *fresh]:
        key = " ".join(str(item.get("title") or "").lower().split())
        if not key or key in seen:
            continue
        seen.add(key)
        combined.append(item)
        if len(combined) >= MAX_ITEMS:
            break

    if not combined:
        raise RuntimeError("dashboard news refresh produced an empty digest")
    payload["generated_at"] = now.isoformat().replace("+00:00", "Z")
    payload["note"] = "Lightweight market refresh plus recent company headlines retained from the last full market build."
    payload["items"] = combined
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"generated_at": payload["generated_at"], "items": len(combined)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
