#!/usr/bin/env python3
"""Defer automated main publication while a code PR is open.

Data-only PRs do not block publication. A PR is considered code-bearing when at
least one changed path is outside data/ and outside the explicit trigger files.
Only code PRs that are currently aligned with main (behind_by == 0) block writes;
stale PRs that already require a rebase never freeze scheduled publication.
Writes are deferred fail-open on API errors so a GitHub API hiccup cannot freeze
all scheduled data publication indefinitely.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


SAFE_PREFIXES = ("data/",)
SAFE_EXACT = {
    ".github/triggers/market-data-rebuild.txt",
    ".github/triggers/market-startup-rebuild.txt",
}


def _request_json(url: str, token: str):
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "vestra-publish-window",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


def _is_safe_path(path: str) -> bool:
    return path in SAFE_EXACT or path.startswith(SAFE_PREFIXES)


def find_blocking_pr(repo: str, token: str):
    pulls = _request_json(
        f"https://api.github.com/repos/{repo}/pulls?state=open&per_page=100",
        token,
    )
    for pr in pulls:
        number = pr.get("number")
        head_sha = str(((pr.get("head") or {}).get("sha")) or "").strip()
        if not number or not head_sha:
            continue
        compare = _request_json(
            f"https://api.github.com/repos/{repo}/compare/main...{head_sha}",
            token,
        )
        # Stale PRs already need a rebase under Vestra's merge rules, so they
        # must not freeze scheduled publication indefinitely. Only a code PR
        # currently aligned with main gets a protected publish window.
        if int(compare.get("behind_by") or 0) > 0:
            continue
        files = _request_json(
            f"https://api.github.com/repos/{repo}/pulls/{number}/files?per_page=100",
            token,
        )
        changed = [str(row.get("filename") or "") for row in files]
        if any(path and not _is_safe_path(path) for path in changed):
            return int(number), changed
    return None, []


def _write_output(name: str, value: str):
    target = os.getenv("GITHUB_OUTPUT")
    if target:
        with open(target, "a", encoding="utf-8") as fh:
            fh.write(f"{name}={value}\n")
    else:
        print(f"{name}={value}")


def main() -> int:
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not repo or not token:
        print("Publish window guard unavailable; proceeding fail-open.")
        _write_output("defer", "false")
        return 0
    try:
        number, changed = find_blocking_pr(repo, token)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
        print(f"Publish window guard API error; proceeding fail-open: {exc}")
        _write_output("defer", "false")
        return 0
    if number is None:
        print("No open code PR blocks automated main publication.")
        _write_output("defer", "false")
        return 0
    print(f"Deferring automated main publication: open code PR #{number}.")
    print("Blocking paths:", ", ".join(changed[:12]))
    _write_output("defer", "true")
    _write_output("blocking_pr", str(number))
    return 0


if __name__ == "__main__":
    sys.exit(main())
