"""Offline deterministic consolidation-episode identity; not a trading signal."""
from datetime import date

def group_episodes(rows: list[dict], cooldown_sessions: int = 20) -> list[dict]:
    """Deduplicate observations by permanent issuer ID and reference session ordinal.

    A new episode requires more than cooldown_sessions since the previous
    observation in the episode. This conservative heuristic does not establish
    structural base independence; historical study must validate episode boundaries.
    """
    if type(cooldown_sessions) is not int or cooldown_sessions < 1:
        raise ValueError("invalid cooldown")
    ordered = sorted(rows, key=lambda r: (r["issuer_id"], r["session_ordinal"], r["signal_date"]))
    result = []
    last = {}
    seen = set()
    for row in ordered:
        issuer = row.get("issuer_id")
        ordinal = row.get("session_ordinal")
        day = row.get("signal_date")
        if not isinstance(issuer, str) or not issuer.strip() or type(ordinal) is not int or ordinal < 0:
            raise ValueError("invalid issuer/session")
        try:
            date.fromisoformat(day)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid signal date") from exc
        key = (issuer, ordinal)
        if key in seen:
            raise ValueError("duplicate issuer/session")
        seen.add(key)
        if issuer in last and ordinal - last[issuer]["last_ordinal"] <= cooldown_sessions:
            current = last[issuer]
            current["last_ordinal"] = ordinal
            current["observation_count"] += 1
        else:
            current = {"episode_id": f"{issuer}:{ordinal}", "issuer_id": issuer,
                       "first_ordinal": ordinal, "last_ordinal": ordinal,
                       "first_signal_date": day, "observation_count": 1}
            result.append(current)
            last[issuer] = current
    return result
