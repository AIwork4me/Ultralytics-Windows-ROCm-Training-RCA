#!/usr/bin/env bash
# Phase-5 warm-performance A/B (ABBA): A = Round-2 C:/bfin (f0f330c4),
# B = Round-3 C:/b58 (d4b574ac). Each leg swaps the wheel DLL, runs the bench
# in a fresh python process, restores the wheel (verified).
set -o pipefail
DRIVER=/c/Users/rocm/Desktop/YOLO_AMD/r3_mission/scripts/swap_run.sh
RAW=/c/Users/rocm/Desktop/YOLO_AMD/r3_mission/raw/perf
mkdir -p "$RAW"
cd /c/Users/rocm/Desktop/YOLO_AMD/r3_mission

for leg in A B B A; do
  case $leg in
    A) DLL=/c/bfin/bin/MIOpen.dll ;;
    B) DLL=/c/b58/bin/MIOpen.dll ;;
  esac
  echo "=== perf leg $leg ($(date -u +%H:%M:%SZ)) ==="
  bash "$DRIVER" "perf_$leg" "$DLL" scripts/perf_bn.py "$RAW/perf_bn_$leg.log"
  echo "leg $leg rc=$?"
done
sha256sum /c/Users/rocm/miniconda3/envs/yolo_amd/Lib/site-packages/_rocm_sdk_libraries/bin/MIOpen.dll
echo "ABBA complete"
