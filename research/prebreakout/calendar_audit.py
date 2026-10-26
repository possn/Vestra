"""Offline point-in-time trading-calendar alignment gate."""
from datetime import date

def audit_event_calendar(events, sessions):
    """Check that event ordinals match a single supplied historical calendar."""
    if not isinstance(sessions,list) or not sessions:
        raise ValueError("missing calendar")
    index={}
    previous=None
    for ordinal,raw in enumerate(sessions):
        if not isinstance(raw,str):
            raise ValueError("invalid calendar date")
        try:
            day=date.fromisoformat(raw)
        except ValueError as exc:
            raise ValueError("invalid calendar date") from exc
        if previous is not None and day<=previous:
            raise ValueError("duplicate or unordered calendar")
        previous=day
        index[raw]=ordinal
    seen=set()
    for event in events:
        if not isinstance(event,dict):
            raise ValueError("invalid event")
        try:
            issuer,episode=event["issuer_id"],event["episode_id"]
            start,finish=event["signal_date"],event["label_end_date"]
            signal,end=event["signal_session"],event["label_end_session"]
        except KeyError as exc:
            raise ValueError("incomplete event") from exc
        if (not isinstance(issuer,str) or not issuer or
                not isinstance(episode,str) or not episode or
                type(signal) is not int or type(end) is not int):
            raise ValueError("invalid identity or ordinal")
        if (issuer,episode) in seen:
            raise ValueError("repeated episode")
        seen.add((issuer,episode))
        if start not in index or finish not in index:
            raise ValueError("event outside calendar")
        if index[start]!=signal or index[finish]!=end or end<signal:
            raise ValueError("event/calendar mismatch")
    return {"status":"calendar_alignment_only_not_source_verified",
            "sessions":len(sessions),"episodes":len(seen)}
