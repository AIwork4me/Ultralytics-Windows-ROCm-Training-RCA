#!/usr/bin/env bash
# Gate L13/L34 helper: run a workload with a FRESH, ISOLATED MIOpen user cache.
# Usage: run_fresh_cache.sh <label> <command...>
#
# Sets MIOPEN_USER_DB_PATH (and HOME/XDG_CACHE_HOME for any other cache) into
# a new tmp dir, records the cache dir contents BEFORE and AFTER, so evidence
# can prove runtime kernel compilation populated the cache during the run
# (not a stale-cache artifact).
set -u
LABEL="$1"; shift
BASE="$HOME/Desktop/YOLO_AMD"
FRESH="$BASE/tmp/miopen_fresh_cache/$LABEL.$$"
mkdir -p "$FRESH"

echo "=== run_fresh_cache label=$LABEL pid=$$ ==="
date -Iseconds
echo "cache dir: $FRESH"
echo "--- cache contents BEFORE (should be empty) ---"
find "$FRESH" -type f | sort

export MIOPEN_USER_DB_PATH="$FRESH"
export XDG_CACHE_HOME="$FRESH/.xdg"
mkdir -p "$XDG_CACHE_HOME"

"$@"
rc=$?

echo "--- cache contents AFTER ---"
find "$FRESH" -type f -printf "%s %p\n" | sort -k2
echo "exit_code=$rc"
exit $rc
