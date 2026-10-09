#!/usr/bin/env bash
# Gate H05 — REAL kthvalue runtime A/B on Linux gfx1151.
# Same dlsym-based harness binary (sha256 4d77a96f...) on BOTH legs; only
# the LD_PRELOADed source-built libMIOpen.so.1 differs. Fresh isolated
# caches per leg. Byte-level dump comparison + CPU-reference correctness
# (the harness exits 0 only if values AND indices match its CPU reference).
set -euo pipefail
WS=/home/amd/Desktop/YOLO_AMD/phase5_3b
BASE=/home/amd/Desktop/YOLO_AMD
SP="$BASE/.venv/lib/python3.13/site-packages"
HARNESS="$BASE/tmp/kthvalue_harness"
EV="$WS/evidence/h05_kthvalue"
mkdir -p "$EV"

HARNESS_SHA=$(sha256sum "$HARNESS" | awk '{print $1}')
echo "[H05] harness sha256: $HARNESS_SHA"

EXPECT_LEG_A=7f282a6f569e31d05708a1b40f298dd60ad39dcbd197794ff24ec478e7f2533b
EXPECT_LEG_B=b14e907a8f259b27e9fc2ebc5fa58120ae90ff179f63a84676ab1a60619e90eb
assert_leg_hash() {
  local leg="$1" want="$2"
  local got; got=$(sha256sum "installs/$leg/lib/libMIOpen.so.1.0" | awk '{print $1}')
  [ "$got" = "$want" ] || { echo "FATAL: $leg libMIOpen.so.1.0 sha256 $got != pinned $want" >&2; exit 9; }
}
assert_leg_hash legA "$EXPECT_LEG_A"
assert_leg_hash legB "$EXPECT_LEG_B"

run_leg() {  # <legA|legB>
  local LEG="$1"
  local INST="$WS/installs/$LEG"
  local FRESH="$WS/tmp/fresh_cache/h05_$LEG"
  rm -rf "$FRESH"; mkdir -p "$FRESH/xdg"
  local LIB="$INST/lib/libMIOpen.so.1"
  local LIBSHA=$(sha256sum "$INST/lib/libMIOpen.so.1.0" | awk '{print $1}')
  echo "[H05] $LEG libMIOpen.so.1.0 sha256: $LIBSHA"
  mkdir -p "$EV/$LEG/dumps"
  set +e
  LD_PRELOAD="$LIB" \
  LD_LIBRARY_PATH="$SP/_rocm_sdk_core/lib:$SP/_rocm_sdk_libraries/lib:$SP/_rocm_sdk_devel/lib:$BASE/.deps/miopen/lib" \
  MIOPEN_CUSTOM_CACHE_DIR="$FRESH" XDG_CACHE_HOME="$FRESH/xdg" \
  MIOPEN_LOG_LEVEL=5 KTHV_DUMP_DIR="$EV/$LEG/dumps" \
  "$HARNESS" > "$EV/$LEG/run.log" 2>&1
  local RC=$?
  set -e
  echo "$RC" > "$EV/$LEG/exit_code.txt"
  echo "[H05] $LEG exit code: $RC"
  grep -m1 'bound miopenKthvalueForward' "$EV/$LEG/run.log" || true
  grep -m2 'algorithm KthvalueFwd\|Loading binary for: "MIOpenKthvalue.cpp.o"' "$EV/$LEG/run.log" || true
  [ "$RC" -eq 0 ] || { echo "[H05] FATAL: $LEG harness failed"; tail -20 "$EV/$LEG/run.log"; exit 5; }
}

run_leg legA
run_leg legB

# ---- byte-level A/B comparison ------------------------------------------
python3 - "$EV" << 'PYEOF'
import hashlib, json, os, sys
ev = sys.argv[1]
def sha(p):
    h = hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda: f.read(1<<20), b''): h.update(c)
    return h.hexdigest()
files_a = sorted(os.listdir(f'{ev}/legA/dumps'))
files_b = sorted(os.listdir(f'{ev}/legB/dumps'))
out = {"gate": "H05", "dumps_legA": files_a, "dumps_legB": files_b,
       "byte_identical": files_a == files_b, "cases": {}}
ok = files_a == files_b and len(files_a) > 0
for fn in files_a:
    a, b = f'{ev}/legA/dumps/{fn}', f'{ev}/legB/dumps/{fn}'
    same = sha(a) == sha(b)
    out["cases"][fn] = {"legA_sha256": sha(a), "legB_sha256": sha(b), "identical": same}
    ok &= same
out["all_byte_identical"] = ok
json.dump(out, open(f'{ev}/ab_dump_comparison.json','w'), indent=2)
print("[H05] A/B byte-identical dumps:", "YES" if ok else "NO", f"({len(files_a)} files)")
sys.exit(0 if ok else 6)
PYEOF
echo "[H05] DONE"
