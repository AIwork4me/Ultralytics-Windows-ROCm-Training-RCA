#!/usr/bin/env bash
# Runtime wrapper for a source-built MIOpen validation leg (W7900 prep).
# Fixes G04-audit MAJOR-1/MAJOR-2 permanently:
#   - prepends the leg's install/lib to LD_LIBRARY_PATH (wheel libMIOpen.so.1
#     in _rocm_sdk_libraries would otherwise shadow the source build)
#   - LD_PRELOADs the leg's libMIOpen.so.1 soname symlink so the source build
#     is FIRST in the global scope (Phase-3 lesson: LD_LIBRARY_PATH alone is
#     insufficient for processes that dlopen libMIOpen by absolute path)
#   - dladdr provenance for miopenKthvalueForward + miopenCreate is echoed
#     IN-STREAM by the harness itself; this wrapper additionally verifies the
#     preloaded object path + sha256 before exec.
# Cache isolation: per-label MIOPEN_CUSTOM_CACHE_DIR + XDG_CACHE_HOME.
#
# Usage: run_validation_leg.sh <baseline|patched> <label> <command...>
set -euo pipefail
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WHICH="$1"; LABEL="$2"; shift 2

case "$WHICH" in
  baseline) INST="$WS/install/baseline" ;;
  patched)  INST="$WS/install/patched" ;;
  *) echo "FATAL: leg must be baseline|patched (got '$WHICH')" >&2; exit 2 ;;
esac
LIB="$INST/lib/libMIOpen.so.1"
if [ ! -e "$LIB" ]; then
  echo "FATAL: $LIB does not exist (leg not built)" >&2; exit 2
fi

source "$WS/scripts/env_rocm7141.sh" >/dev/null

FRESH="$WS/runtime/${WHICH}-cache/$LABEL"
# G06/G07-review NIT fix: refuse to reuse a cache dir that contains ANY file
# (including under xdg/, where comgr/llvm caches land) unless FORCE.
if [ -e "$FRESH" ]; then
  n_files=$(find "$FRESH" -type f 2>/dev/null | wc -l)
  if [ "$n_files" -gt 0 ] && [ "${FRESH_CACHE_FORCE:-0}" != "1" ]; then
    echo "FATAL: cache dir $FRESH already holds $n_files file(s) (stale-cache risk). Use a new label or FRESH_CACHE_FORCE=1." >&2
    exit 2
  fi
fi
mkdir -p "$FRESH/xdg"

export LD_PRELOAD="$LIB"
export LD_LIBRARY_PATH="$INST/lib:$LD_LIBRARY_PATH"
export MIOPEN_CUSTOM_CACHE_DIR="$FRESH"
export MIOPEN_USER_DB_PATH="$FRESH"
export XDG_CACHE_HOME="$FRESH/xdg"

echo "=== run_validation_leg($WHICH,$LABEL) pid=$$ $(date -Iseconds) ==="
echo "LD_PRELOAD=$LD_PRELOAD"
echo "libMIOpen sha256: $(sha256sum "$LIB" | cut -d' ' -f1)"
echo "cache dir: $FRESH (fresh per label; never shared across legs)"
exec "$@"
