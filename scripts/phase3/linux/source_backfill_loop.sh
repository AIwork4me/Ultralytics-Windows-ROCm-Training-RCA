#!/usr/bin/env bash
# Persistent self-healing source backfill for a flaky-network night.
# Alternates two transports until every needed blob of <sha>:<filter> is in
# the object store, then checks out:
#   A) git batch transport (promisor lazy fetch via `git checkout`)
#   B) raw.githubusercontent.com per-file fetch with SHA-1 verification
# Safe to kill/restart at any time; all progress is cumulative.
set -u
REPO="$1"; SHA="$2"; FILTER="$3"
cd "$REPO" || exit 1

missing_count() {
  git -c gc.auto=0 ls-tree -r "$SHA" "$FILTER" | awk '$2=="blob"{print $3}' \
    | git -c gc.auto=0 cat-file --batch-check='%(objectname) %(objecttype)' 2>/dev/null \
    | awk '$2!="blob"{n++} END{print n+0}'
}

raw_pass() {
  local list
  list=$(mktemp)
  # only files whose blob is missing
  git -c gc.auto=0 ls-tree -r "$SHA" "$FILTER" | awk -v OFS='\t' '$2=="blob"{print $3,$4}' > "$list.all"
  : > "$list"
  while IFS=$'\t' read -r sha path; do
    git -c gc.auto=0 cat-file -e "$sha" 2>/dev/null || printf '%s\t%s\n' "$sha" "$path" >> "$list"
  done < "$list.all"
  local n; n=$(wc -l < "$list"); echo "[$(date +%T)] raw pass: $n files to fetch"
  [ "$n" -eq 0 ] && { rm -f "$list" "$list.all"; return 0; }
  export SHA
  fetch_one() {
    local sha="$1" path="$2" tmp got a
    tmp=$(mktemp)
    for a in 1 2 3; do
      if curl -sfL --max-time 40 "https://raw.githubusercontent.com/ROCm/rocm-libraries/$SHA/$path" -o "$tmp" 2>/dev/null; then
        got=$(git -c gc.auto=0 hash-object -w "$tmp" 2>/dev/null)
        [ "$got" = "$sha" ] && { rm -f "$tmp"; return 0; }
      fi
      sleep "$a"
    done
    rm -f "$tmp"; return 1
  }
  export -f fetch_one
  cat "$list" | tr '\t' ' ' | xargs -P 10 -n 2 bash -c 'fetch_one "$0" "$1"' 2>/dev/null
  rm -f "$list" "$list.all"
}

git_pass() {
  echo "[$(date +%T)] git batch attempt"
  git config remote.origin.promisor true
  git config remote.origin.partialclonefilter blob:none
  timeout 240 git -c gc.auto=0 checkout -q "$SHA" 2>&1 | tail -1
  # disable promisor again so local checks never hang
  git config remote.origin.promisor false
  git config --unset remote.origin.partialclonefilter 2>/dev/null || true
}

for round in $(seq 1 40); do
  m=$(missing_count)
  echo "[$(date +%T)] round $round: missing=$m"
  [ "$m" -eq 0 ] && break
  raw_pass
  m=$(missing_count)
  echo "[$(date +%T)] after raw: missing=$m"
  [ "$m" -eq 0 ] && break
  git_pass
done

m=$(missing_count)
echo "[$(date +%T)] final missing=$m"
if [ "$m" -eq 0 ]; then
  git -c gc.auto=0 checkout -q "$SHA" 2>&1 | tail -1
  echo "HEAD: $(git rev-parse HEAD)"
  git -c gc.auto=0 status --short | head -3
  echo "BACKFILL_COMPLETE"
else
  echo "BACKFILL_INCOMPLETE"
  exit 2
fi
