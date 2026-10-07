#!/usr/bin/env bash
# Backfill a blobless git clone's missing blobs for a path filter using
# raw.githubusercontent.com (survives nights when the git smart protocol is
# unusable). Every file is verified against the tree's expected blob SHA-1
# before being written into the object store, so the resulting worktree is
# byte-identical to a network checkout of the same SHA.
#
# Usage: raw_backfill_checkout.sh <repo-dir> <sha> <path-filter>
set -u
REPO="$1"; SHA="$2"; FILTER="$3"
cd "$REPO" || exit 1

LIST=$(mktemp)
git -c gc.auto=0 ls-tree -r "$SHA" "$FILTER" | awk '$2=="blob"{print $3"\t"$4}' > "$LIST"
TOTAL=$(wc -l < "$LIST")
echo "files to ensure: $TOTAL"

fetch_one() {
  local sha="$1" path="$2"
  # already present?
  if git -c gc.auto=0 cat-file -e "$sha" 2>/dev/null; then return 0; fi
  local tmp
  tmp=$(mktemp)
  for attempt in 1 2 3 4 5; do
    if curl -sfL --max-time 45 \
        "https://raw.githubusercontent.com/ROCm/rocm-libraries/$SHA/$path" -o "$tmp"; then
      # verify and write into object store in one step
      local got
      got=$(git -c gc.auto=0 hash-object -w "$tmp") || { sleep 3; continue; }
      if [ "$got" = "$sha" ]; then
        rm -f "$tmp"; return 0
      fi
      echo "SHA-MISMATCH $path (expected $sha got $got)" >&2
    fi
    sleep $((attempt * 2))
  done
  rm -f "$tmp"
  echo "FAILED $path $sha" >&2
  return 1
}
export -f fetch_one

# process in N parallel streams
FAIL=0
cat "$LIST" | tr '\t' ' ' | xargs -P 8 -n 2 bash -c 'fetch_one "$0" "$1"' || FAIL=1
rm -f "$LIST"

# verify: no missing blobs remain under the filter
MISSING=$(git -c gc.auto=0 ls-tree -r "$SHA" "$FILTER" | awk '$2=="blob"{print $3}' | while read -r s; do
  git -c gc.auto=0 cat-file -e "$s" 2>/dev/null || echo "$s"
done | wc -l)
echo "missing blobs after backfill: $MISSING"
[ "$MISSING" -eq 0 ] || exit 2

# now the checkout needs no network
git -c gc.auto=0 checkout -q "$SHA" 2>&1 | tail -1
echo "HEAD: $(git rev-parse HEAD)"
git -c gc.auto=0 status --short | head -3
echo "BACKFILL_OK"
