#!/usr/bin/env bash
# Wheel-swap legs: D (BatchNorm) + F (YOLO26n coco8) on the patched DLL.
# Wheel DLL is backed up first, swapped with the pinned build's MIOpen.dll,
# and restored + hash-verified afterwards.
set -o pipefail
WHEEL=/c/Users/rocm/miniconda3/envs/yolo_amd/Lib/site-packages/_rocm_sdk_libraries/bin/MIOpen.dll
BACKUP=/c/Users/rocm/Desktop/YOLO_AMD/fin_mission/backup
RAW=/c/Users/rocm/Desktop/YOLO_AMD/fin_mission/raw
PY=/c/Users/rocm/miniconda3/envs/yolo_amd/python.exe
PRISTINE=74b4ee038803606e6ea4846362a8565fa9e286cb0df18cf80b9e5a7657b78f0a
PATCHED=c739cb0e143162694c331ef8137e686418d003769ed7ad25c96945fe63a6fb42
mkdir -p "$BACKUP"

echo "=== pre-swap wheel hash (expect $PRISTINE) ==="
sha256sum "$WHEEL"
cp "$WHEEL" "$BACKUP/MIOpen.dll.wheel.bak"

echo "=== swap in patched DLL (expect $PATCHED after copy) ==="
cp /c/bfin/bin/MIOpen.dll "$WHEEL"
sha256sum "$WHEEL"

cd /c/Users/rocm/Desktop/YOLO_AMD/fin_mission
echo "=== D: BatchNorm fwd/bwd vs CPU reference ==="
"$PY" scripts/d_batchnorm.py > "$RAW/batchnorm/D_batchnorm_patched.log" 2>&1
echo "D exit=$?"
tail -8 "$RAW/batchnorm/D_batchnorm_patched.log"

echo "=== F: YOLO26n coco8 1-epoch smoke train ==="
"$PY" scripts/f_yolo26n_coco8.py > "$RAW/yolo/F_yolo26n_coco8.log" 2>&1
echo "F exit=$?"
tail -6 "$RAW/yolo/F_yolo26n_coco8.log"

echo "=== restore wheel DLL (expect $PRISTINE) ==="
cp "$BACKUP/MIOpen.dll.wheel.bak" "$WHEEL"
sha256sum "$WHEEL"
