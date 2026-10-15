#!/usr/bin/env python3
"""Refuse to publish transition metadata inconsistent with immutable archives."""
import json
from pathlib import Path
from build_prebreakout_transitions import build

ROOT=Path(__file__).resolve().parents[1]

def verify(root:Path=ROOT):
    path=root/"data"/"prebreakout-transitions.json"
    published=json.loads(path.read_text(encoding="utf-8"))
    expected=build(root/"data"/"prebreakout-history")
    if published!=expected:
        raise ValueError("published transitions differ from immutable scan archives")
    if published.get("historical_only") is not True:
        raise ValueError("stage transition ledger must be historical-only")
    return {"scans_considered":published["scans_considered"],"events":len(published["events"])}

if __name__=="__main__":
    print(json.dumps(verify()))
