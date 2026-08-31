#!/usr/bin/env bash
set -euo pipefail

# Publish the current commit to a shared branch without losing work when another
# data workflow updates that branch between our checkout and push.
#
# Usage: publish_with_retry.sh [remote] [branch]
# Environment:
#   PUBLISH_PUSH_ATTEMPTS       Number of push attempts (default: 6)
#   PUBLISH_PUSH_DELAY_SECONDS  Base retry delay in seconds (default: 5)

remote="${1:-origin}"
branch="${2:-main}"
attempts="${PUBLISH_PUSH_ATTEMPTS:-6}"
base_delay="${PUBLISH_PUSH_DELAY_SECONDS:-5}"

if ! [[ "$attempts" =~ ^[1-9][0-9]*$ ]]; then
  echo "PUBLISH_PUSH_ATTEMPTS must be a positive integer" >&2
  exit 2
fi
if ! [[ "$base_delay" =~ ^[0-9]+$ ]]; then
  echo "PUBLISH_PUSH_DELAY_SECONDS must be a non-negative integer" >&2
  exit 2
fi

for ((attempt=1; attempt<=attempts; attempt++)); do
  echo "Publish attempt ${attempt}/${attempts}: syncing ${remote}/${branch}..."
  git fetch "$remote" "$branch"

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
