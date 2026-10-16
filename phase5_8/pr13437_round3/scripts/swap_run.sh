#!/usr/bin/env bash
# Round-3 wheel-DLL swap run driver with archived transcript + guaranteed restore.
# Usage: swap_run.sh <variant-label> <build-dll-path> <py-script> <log-path>
# e.g.  swap_run.sh r3 /c/b58/bin/MIOpen.dll scripts/d_batchnorm.py raw/batchnorm/D_r3.log
set -o pipefail
WHEEL=/c/Users/rocm/miniconda3/envs/yolo_amd/Lib/site-packages/_rocm_sdk_libraries/bin/MIOpen.dll
BACKUP=/c/Users/rocm/Desktop/YOLO_AMD/fin_mission/backup/MIOpen.dll.wheel.bak
PY=/c/Users/rocm/miniconda3/envs/yolo_amd/python.exe
LABEL=$1; DLL=$2; SCRIPT=$3; LOG=$4
TS="$LOG.swap_transcript"
cd /c/Users/rocm/Desktop/YOLO_AMD/r3_mission

restore() {
  {
  echo "--- restore wheel DLL (guaranteed cleanup, UTC $(date -u +%Y-%m-%dT%H:%M:%SZ)) ---"
  cp "$BACKUP" "$WHEEL"
  sha256sum "$WHEEL" "$BACKUP"
  } >> "$TS" 2>&1
}
trap restore EXIT

{
echo "=== $LABEL swap transcript (UTC $(date -u +%Y-%m-%dT%H:%M:%SZ)) ==="
echo "--- pre-swap wheel hash (expect 74b4ee03...) ---"
sha256sum "$WHEEL"
echo "--- swap in $DLL ---"
cp "$DLL" "$WHEEL"
sha256sum "$WHEEL"
} > "$TS" 2>&1

"$PY" "$SCRIPT" 2>&1 | tee "$LOG"
RC=${PIPESTATUS[0]}
echo "$LABEL exit=$RC" | tee -a "$TS"
trap - EXIT; restore
exit $RC
