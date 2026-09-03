#!/usr/bin/env bash
set -euo pipefail

# Publish the current commit to a shared branch without losing work when another
# data workflow updates that branch between our checkout and push.
#
# Usage: publish_with_retry.sh [remote] [branch]
# Environment:
#   PUBLISH_PUSH_ATTEMPTS       Number of push attempts (default: 6)
#   PUBLISH_PUSH_DELAY_SECONDS  Base retry delay in seconds (default: 5)
#   PUBLISH_SUPERSEDE_COMMIT_PREFIX
#                               Optional commit-subject prefix that identifies a
#                               snapshot stream. If the remote already contains
#                               a newer commit from that same stream since this
#                               local commit's base, publication exits cleanly as
#                               superseded instead of rebasing snapshot-on-snapshot.
#
# Canonical Vestra market snapshots opt in automatically through their exact,
# stable commit prefix. Other publishers keep the historical rebase behaviour.

remote="${1:-origin}"
branch="${2:-main}"
attempts="${PUBLISH_PUSH_ATTEMPTS:-6}"
base_delay="${PUBLISH_PUSH_DELAY_SECONDS:-5}"
market_snapshot_prefix="Actualização automática de dados de mercado ("
local_subject="$(git log -1 --format=%s)"
supersede_prefix="${PUBLISH_SUPERSEDE_COMMIT_PREFIX:-}"

if [[ -z "$supersede_prefix" && "$local_subject" == "$market_snapshot_prefix"* ]]; then
  supersede_prefix="$market_snapshot_prefix"
fi

if ! [[ "$attempts" =~ ^[1-9][0-9]*$ ]]; then
  echo "PUBLISH_PUSH_ATTEMPTS must be a positive integer" >&2
  exit 2
fi
if ! [[ "$base_delay" =~ ^[0-9]+$ ]]; then
  echo "PUBLISH_PUSH_DELAY_SECONDS must be a non-negative integer" >&2
  exit 2
fi

# Capture the immutable base before any rebase attempt. A queued market workflow
# can start from an old event SHA; if another canonical market snapshot is later
# published on top of that base, the queued snapshot is redundant. Rebasing two
# full generated snapshots is both conflict-prone and semantically ambiguous.
publish_base=""
if [[ -n "$supersede_prefix" ]]; then
  publish_base="$(git rev-parse HEAD^ 2>/dev/null || true)"
fi

for ((attempt=1; attempt<=attempts; attempt++)); do
  echo "Publish attempt ${attempt}/${attempts}: syncing ${remote}/${branch}..."
  git fetch "$remote" "$branch"

  if [[ -n "$supersede_prefix" && -n "$publish_base" ]] \
      && git merge-base --is-ancestor "$publish_base" "$remote/$branch"; then
    remote_subjects="$(git log --format=%s "${publish_base}..${remote}/${branch}")"
    if grep -Fq "$supersede_prefix" <<<"$remote_subjects"; then
      echo "Publication superseded: ${remote}/${branch} already contains a newer snapshot matching '${supersede_prefix}'."
      echo "Keeping the remote snapshot and refusing snapshot-on-snapshot rebase."
      exit 0
    fi
  fi

  # Rebase our generated-data commit on top of the latest main. Distinct feeds
  # normally touch distinct files, so this resolves the expected writer race
  # while still failing loudly on a genuine content conflict.
  if ! git rebase "$remote/$branch"; then
    git rebase --abort || true
    echo "Rebase conflict while publishing. Refusing to overwrite remote data." >&2
    exit 1
  fi

  if git push "$remote" "HEAD:${branch}"; then
    echo "Published successfully on attempt ${attempt}."
    exit 0
  fi

  if (( attempt == attempts )); then
    break
  fi

  # A push can lose a race even immediately after a successful fetch/rebase.
  # Back off progressively and retry against the new remote tip.
  delay=$((base_delay * attempt))
  echo "Remote advanced during push; retrying in ${delay}s..."
  sleep "$delay"
done

echo "Failed to publish after ${attempts} attempts." >&2
exit 1
