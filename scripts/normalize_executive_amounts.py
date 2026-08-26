from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data" / "executives.json"

FLEX_RANGE = re.compile(r"\$\s*([0-9][0-9,.]*)\s*(?:-|–|—|to)\s*\$?\s*([0-9][0-9,.]*)", re.I)


def money_int(value: str) -> int | None:
    raw = re.sub(r"[^0-9]", "", value or "")
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def canonical(lo: int, hi: int) -> str:
    return f"${lo:,} - ${hi:,}"


def amount_from_text(text: str) -> tuple[int, int] | None:
    for match in FLEX_RANGE.finditer(text or ""):
        lo, hi = money_int(match.group(1)), money_int(match.group(2))
        if lo is not None and hi is not None and hi >= lo:
            return lo, hi
    return None


def normalize_trade(row: dict) -> dict:
    out = dict(row)
    current = amount_from_text(str(out.get("amount") or ""))
    # OCR can turn 15,000 into 15 or render the thousands separator as a dot.
    # The asset text is the original extracted filing row, so use it whenever the
    # serialized interval is absent, reversed or implausibly truncated.
    suspicious = current is None or current[1] < current[0] or (current[0] >= 1000 and current[1] < 1000)
    source = amount_from_text(str(out.get("asset") or "")) if suspicious else None
    chosen = source or current
    if chosen:
        out["amount"] = canonical(*chosen)
    if str(out.get("chamber") or "") == "Executive":
        out.setdefault("member_key", "executive:donald-trump")
    return out


def main() -> None:
    if not PATH.exists():
        raise SystemExit("executives.json missing")
    data = json.loads(PATH.read_text(encoding="utf-8"))
    trades = [normalize_trade(x) for x in (data.get("trades") or []) if isinstance(x, dict)]
    data["trades"] = trades
    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Normalized executive amount ranges: {len(trades)} rows")


if __name__ == "__main__":
    main()
