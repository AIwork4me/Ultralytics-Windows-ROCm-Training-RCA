#!/usr/bin/env bash
# Gate H06 — direct public-API BatchNorm A/B on Linux gfx1151.
# W7900 harness recompiled from source against the R2 tree's public
# headers; identical binary on both legs; fixed predeclared tolerances;
# fresh isolated caches; MIOPEN_LOG_LEVEL=6 for dispatch proof.
set -euo pipefail
WS=/home/amd/Desktop/YOLO_AMD/phase5_3b
BASE=/home/amd/Desktop/YOLO_AMD
SP="$BASE/.venv/lib/python3.13/site-packages"
HARNESS="$WS/tmp/batchnorm_harness"
EV="$WS/evidence/h06_batchnorm"
mkdir -p "$EV"
echo "[H06] harness sha256: $(sha256sum "$HARNESS" | awk '{print $1}')"

EXPECT_LEG_A=7f282a6f569e31d05708a1b40f298dd60ad39dcbd197794ff24ec478e7f2533b
EXPECT_LEG_B=b14e907a8f259b27e9fc2ebc5fa58120ae90ff179f63a84676ab1a60619e90eb
assert_leg_hash() {
  local leg="$1" want="$2"
  local got; got=$(sha256sum "installs/$leg/lib/libMIOpen.so.1.0" | awk '{print $1}')
  [ "$got" = "$want" ] || { echo "FATAL: $leg libMIOpen.so.1.0 sha256 $got != pinned $want" >&2; exit 9; }
}
assert_leg_hash legA "$EXPECT_LEG_A"
assert_leg_hash legB "$EXPECT_LEG_B"

run_leg() {
  local LEG="$1"
  local INST="$WS/installs/$LEG"
  local FRESH="$WS/tmp/fresh_cache/h06_$LEG"
  rm -rf "$FRESH"; mkdir -p "$FRESH/xdg"
  local LIB="$INST/lib/libMIOpen.so.1"
  echo "[H06] $LEG libMIOpen.so.1.0 sha256: $(sha256sum "$INST/lib/libMIOpen.so.1.0" | awk '{print $1}')"
  set +e
  LD_PRELOAD="$LIB" \
  LD_LIBRARY_PATH="$SP/_rocm_sdk_core/lib:$SP/_rocm_sdk_libraries/lib:$SP/_rocm_sdk_devel/lib:$BASE/.deps/miopen/lib" \
  MIOPEN_CUSTOM_CACHE_DIR="$FRESH" XDG_CACHE_HOME="$FRESH/xdg" \
  MIOPEN_LOG_LEVEL=6 \
  "$HARNESS" > "$EV/$LEG.run.log" 2>&1
  local RC=$?
  set -e
  echo "$RC" > "$EV/$LEG.exit_code.txt"
  echo "[H06] $LEG exit code: $RC"
  grep -m2 'miopenBatchNormalizationForwardTraining <-\|miopenBatchNormalizationBackward <-' "$EV/$LEG.run.log" || true
  grep -m2 'MIOpenBatchNormFwdTrainSpatial\|MIOpenBatchNormBwdSpatial' "$EV/$LEG.run.log" | head -2 || true
  [ "$RC" -eq 0 ] || { echo "[H06] FATAL: $LEG failed"; tail -25 "$EV/$LEG.run.log"; exit 5; }
}

run_leg legA
run_leg legB

python3 - "$EV" << 'PYEOF'
import json, re, sys
ev = sys.argv[1]
def parse(leg):
    txt = open(f'{ev}/{leg}.run.log').read()
    out = {"exit": open(f'{ev}/{leg}.exit_code.txt').read().strip()}
    for k in ("y","dx","dw","db","running_mean","running_variance"):
        m = re.search(rf'{k}[^\d-]*(-?[\d.e+-]+)', txt)
        if m: out[f"err_{k}"] = m.group(1)
    out["fwd_dispatch"] = bool(re.search(r'MIOpenBatchNormFwdTrainSpatial', txt))
    out["bwd_dispatch"] = bool(re.search(r'MIOpenBatchNormBwdSpatial', txt))
    out["bound_fwd"] = re.search(r'miopenBatchNormalizationForwardTraining <- (\S+)', txt).group(1) if re.search(r'miopenBatchNormalizationForwardTraining <- (\S+)', txt) else None
    out["bound_bwd"] = re.search(r'miopenBatchNormalizationBackward <- (\S+)', txt).group(1) if re.search(r'miopenBatchNormalizationBackward <- (\S+)', txt) else None
    return out
a, b = parse("legA"), parse("legB")
json.dump({"gate":"H06","legA":a,"legB":b,
           "same_binding_paths": a["bound_fwd"]==b["bound_fwd"] and a["bound_bwd"]==b["bound_bwd"],
           "numerics_equal_across_legs": all(a.get(k)==b.get(k) for k in a if k.startswith("err_"))},
          open(f'{ev}/batchnorm_ab.json','w'), indent=2)
print("[H06] legA errors:", {k:v for k,v in a.items() if k.startswith('err_')})
print("[H06] legB errors:", {k:v for k,v in b.items() if k.startswith('err_')})
print("[H06] dispatch fwd/bwd:", a["fwd_dispatch"], a["bwd_dispatch"])
PYEOF
echo "[H06] DONE"
