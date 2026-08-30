"""Audit top-level JavaScript runtime reachability for the Vestra PWA.

This is deliberately conservative: it discovers direct local <script src>
entries in index.html, then follows literal .js references only from already-
reachable JS. External CDN scripts are ignored. Service Worker and Cloudflare
Worker entrypoints are classified separately. Unreferenced files are reported,
not deleted automatically.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

SCRIPT_SRC_RE = re.compile(r'<script\b[^>]*\bsrc=["\']([^"\']+?\.js)(?:\?[^"\']*)?["\']', re.I)
JS_LITERAL_RE = re.compile(r'["\']([A-Za-z0-9_.-]+\.js)(?:\?[^"\']*)?["\']')
EXTERNAL_RE = re.compile(r'^(?:https?:)?//', re.I)

SPECIAL_ENTRYPOINTS = {"sw.js": "service_worker", "worker.js": "cloudflare_worker"}


def _basename(ref: str) -> str:
    return ref.split("/")[-1].split("?")[0]


def direct_scripts() -> list[str]:
    html = INDEX.read_text(encoding="utf-8")
    local_refs = (x for x in SCRIPT_SRC_RE.findall(html) if not EXTERNAL_RE.match(x))
    return list(dict.fromkeys(_basename(x) for x in local_refs))


def dynamic_reachable(seed: list[str]) -> tuple[set[str], dict[str, list[str]], list[str]]:
    reachable = set(seed)
    edges: dict[str, list[str]] = {}
    missing: list[str] = []
    queue = list(seed)
    while queue:
        name = queue.pop(0)
        path = ROOT / name
        if not path.exists():
            missing.append(name)
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        refs = []
        for ref in JS_LITERAL_RE.findall(text):
            target = _basename(ref)
            if target == name:
                continue
            candidate = ROOT / target
            if not candidate.exists():
                continue
            refs.append(target)
            if target not in reachable and target not in SPECIAL_ENTRYPOINTS:
                reachable.add(target)
                queue.append(target)
        if refs:
            edges[name] = sorted(set(refs))
    return reachable, edges, sorted(set(missing))


def build_report() -> dict:
    all_top_level = sorted(p.name for p in ROOT.glob("*.js") if p.is_file())
    direct = direct_scripts()
    reachable, edges, missing = dynamic_reachable(direct)
    dynamic = sorted(reachable - set(direct))
    special = {name: kind for name, kind in SPECIAL_ENTRYPOINTS.items() if (ROOT / name).exists()}
    unreferenced = sorted(set(all_top_level) - reachable - set(special))
    return {
        "schema_version": 1,
        "top_level_js_count": len(all_top_level),
        "direct_count": len(direct),
        "dynamic_count": len(dynamic),
        "special_count": len(special),
        "unreferenced_count": len(unreferenced),
        "direct": direct,
        "dynamic": dynamic,
        "special": special,
        "unreferenced": unreferenced,
        "edges": edges,
        "missing_direct": missing,
    }


def main() -> int:
    report = build_report()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if report["missing_direct"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
