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


def trade_key(row: dict) -> tuple:
    return (
        str(row.get("member_key") or row.get("member") or ""),
        str(row.get("ticker") or "").upper(),
        str(row.get("type") or "").lower(),
        str(row.get("amount") or ""),
        str(row.get("transaction_date") or ""),
        str(row.get("disclosure_date") or ""),
    )


def main() -> None:
    if not PATH.exists():
        raise SystemExit("executives.json missing")
    data = json.loads(PATH.read_text(encoding="utf-8"))
    normalized = [normalize_trade(x) for x in (data.get("trades") or []) if isinstance(x, dict)]

    deduped: dict[tuple, dict] = {}
    for row in normalized:
        deduped[trade_key(row)] = row
    trades = list(deduped.values())
    trades.sort(key=lambda x: (x.get("disclosure_date") or "", x.get("transaction_date") or "", x.get("ticker") or ""), reverse=True)
    data["trades"] = trades

    buys = sum(1 for x in trades if x.get("type") == "buy")
    sells = sum(1 for x in trades if x.get("type") == "sell")
    newest = max((str(x.get("disclosure_date") or "") for x in trades), default="")
    data["newest_disclosure"] = newest
    for person in data.get("people") or []:
        if person.get("key") == "executive:donald-trump":
            person["count"] = len(trades)
            person["buys"] = buys
            person["sells"] = sells
            person["last"] = newest

    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Normalized/deduplicated executive feed: {len(trades)} rows ({buys} buys / {sells} sells)")


if __name__ == "__main__":
    main()
