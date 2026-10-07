#!/usr/bin/env bash
# Gate L29/L34/L38/L39 helper: run a workload in a child process where the
# SOURCE-BUILT MIOpen (unpatched or patched) demonstrably loads instead of
# the wheel's, with every ROCm dependency resolving to the controlled wheel
# stack (system /opt/rocm-7.2.1 must never leak in).
#
# Usage: run_with_source_miopen.sh <unpatched|patched> <command...>
set -u
WHICH="$1"; shift
BASE="$HOME/Desktop/YOLO_AMD"
SP="$BASE/.venv/lib/python3.13/site-packages"
I="$BASE/installs/miopen-$WHICH"

export LD_LIBRARY_PATH="$I/lib:$SP/_rocm_sdk_core/lib:$SP/_rocm_sdk_libraries/lib:$SP/_rocm_sdk_devel/lib:$BASE/.deps/miopen/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
echo "=== run_with_source_miopen($WHICH) pid=$$ ==="
date -Iseconds
echo "expect libMIOpen from: $I/lib"
echo "--- ldd sanity (ROCm deps) ---"
ldd "$I/lib/libMIOpen.so.1.0" 2>/dev/null | grep -E "libMIOpen|hiprtc|comgr|rocblas|amdhip" || true
echo "--- run ---"
exec "$@"
