#!/usr/bin/env bash
# Self-healing blob backfill for the blobless rocm-libraries clone.
# Tries `git checkout -f <sha>` repeatedly; each promisor lazy-fetch is
# cumulative. Raw.githubusercontent fallback is NOT available on this
# machine (blocked), so transport = git smart HTTP batch fetch with retries.
set -u
WS=/workspace/miopen-w7900-validation
REPO="$WS/repos/rocm-libraries"
SHA="${1:-b68f8944300f104875d953fc8e4510908c9aaf0b}"
LOG="$WS/logs/G04_repo_backfill.log"
cd "$REPO" || exit 1
git config remote.origin.promisor true
git config remote.origin.partialclonefilter blob:none
: > "$LOG"
for round in $(seq 1 120); do
  if timeout 280 git -c gc.auto=0 checkout -qf "$SHA" >> "$LOG" 2>&1; then
    echo "[$(date -Is)] CHECKOUT_OK round=$round" >> "$LOG"
    git status --short | head -3 >> "$LOG"
    exit 0
  fi
  echo "[$(date -Is)] round=$round retry" >> "$LOG"
  sleep 15
done
echo "BACKFILL_INCOMPLETE" >> "$LOG"
exit 2
