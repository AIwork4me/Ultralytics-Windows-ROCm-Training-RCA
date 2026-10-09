#!/usr/bin/env bash
# Run a workload in a child process where the SOURCE-BUILT MIOpen
# (unpatched|patched) demonstrably services the calls, with every ROCm
# dependency resolving to the controlled 7.14 wheel stack.
#
# Binding mechanism (fixed after adversarial review): LD_PRELOAD of the
# SONAME symlink — LD_LIBRARY_PATH alone is INSUFFICIENT because the wheel
# stack dlopens libMIOpen.so.1 by absolute path (see
# evidence/phase3/raw/linux/runtime_unpatched/source_load_probe.txt).
# The preload makes the source build the first object in the global scope;
# dladdr(miopenCreate) is echoed INTO the evidence stream to prove binding.
#
# Also isolates the MIOpen cache per label (MIOPEN_CUSTOM_CACHE_DIR) and
# XDG_CACHE_HOME so runs cannot share kernels.
#
# Usage: run_with_source_miopen.sh <unpatched|patched> <label> <command...>
set -u
WHICH="$1"; LABEL="$2"; shift 2
BASE="$HOME/Desktop/YOLO_AMD"
SP="$BASE/.venv/lib/python3.13/site-packages"
I="$BASE/installs/miopen-$WHICH"
FRESH="$BASE/tmp/miopen_fresh_cache/$LABEL"
mkdir -p "$FRESH"

export LD_PRELOAD="$I/lib/libMIOpen.so.1"
export LD_LIBRARY_PATH="$SP/_rocm_sdk_core/lib:$SP/_rocm_sdk_libraries/lib:$SP/_rocm_sdk_devel/lib:$BASE/.deps/miopen/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export MIOPEN_CUSTOM_CACHE_DIR="$FRESH"
export XDG_CACHE_HOME="$FRESH/xdg"
mkdir -p "$XDG_CACHE_HOME"

echo "=== run_with_source_miopen($WHICH,$LABEL) pid=$$ $(date -Iseconds) ==="
echo "LD_PRELOAD=$LD_PRELOAD"
python3 - "$I" <<'PYEOF'
import ctypes, sys
class Dl(ctypes.Structure):
    _fields_=[('f',ctypes.c_char_p),('b',ctypes.c_void_p),('s',ctypes.c_char_p),('a',ctypes.c_void_p)]
libc=ctypes.CDLL(None); dl=ctypes.CDLL('libdl.so.2'); i=Dl()
ok=dl.dladdr(ctypes.cast(libc.miopenCreate,ctypes.c_void_p),ctypes.byref(i))
print(f"bound miopenCreate -> {i.f.decode() if ok and i.f else 'UNKNOWN'}",
      "(MATCH)" if ok and i.f and sys.argv[1] in i.f.decode() else "(MISMATCH!)")
PYEOF
exec "$@"
