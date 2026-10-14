#!/usr/bin/env bash
# D v2: BatchNorm rerun with archived swap transcript (wheel swap -> run -> restore).
set -o pipefail
WHEEL=/c/Users/rocm/miniconda3/envs/yolo_amd/Lib/site-packages/_rocm_sdk_libraries/bin/MIOpen.dll
BACKUP=/c/Users/rocm/Desktop/YOLO_AMD/fin_mission/backup
RAW=/c/Users/rocm/Desktop/YOLO_AMD/fin_mission/raw
PY=/c/Users/rocm/miniconda3/envs/yolo_amd/python.exe
TS=$RAW/batchnorm/swap_transcript_v2.log

{
echo "=== D v2 swap transcript (UTC $(date -u +%Y-%m-%dT%H:%M:%SZ)) ==="
echo "--- pre-swap wheel hash (expect 74b4ee03...) ---"
sha256sum "$WHEEL"
echo "--- swap in pinned-build DLL ---"
cp /c/bfin/bin/MIOpen.dll "$WHEEL"
sha256sum "$WHEEL"
echo "--- run d_batchnorm.py (banner + timestamped) ---"
} 2>&1 | tee "$TS"

cd /c/Users/rocm/Desktop/YOLO_AMD/fin_mission
"$PY" scripts/d_batchnorm.py 2>&1 | tee "$RAW/batchnorm/D_batchnorm_patched_v2.log"
DRC=${PIPESTATUS[0]}
echo "D v2 exit=$DRC" | tee -a "$TS"

{
echo "--- restore wheel DLL ---"
cp "$BACKUP/MIOpen.dll.wheel.bak" "$WHEEL"
sha256sum "$WHEEL"
echo "--- backup file hash (expect 74b4ee03...) ---"
sha256sum "$BACKUP/MIOpen.dll.wheel.bak"
echo "=== transcript end (UTC $(date -u +%Y-%m-%dT%H:%M:%SZ)) ==="
} 2>&1 | tee -a "$TS"
exit $DRC
