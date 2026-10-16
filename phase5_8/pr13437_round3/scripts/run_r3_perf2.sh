#!/usr/bin/env bash
# Perf v2 ABBA via DLL preload (wheel untouched). Legs: A B B A with unique files.
set -o pipefail
PY=/c/Users/rocm/miniconda3/envs/yolo_amd/python.exe
RAW=/c/Users/rocm/Desktop/YOLO_AMD/r3_mission/raw/perf
cd /c/Users/rocm/Desktop/YOLO_AMD/r3_mission
i=0
for leg in A B B A; do
  i=$((i+1))
  case $leg in A) DLL='C:\bfin\bin\MIOpen.dll';; B) DLL='C:\b58\bin\MIOpen.dll';; esac
  echo "=== leg $i=$leg ($(date -u +%H:%M:%SZ)) ==="
  "$PY" scripts/perf_bn2.py "$DLL" "$leg" > "$RAW/perf2_${leg}_$i.log" 2>&1
  echo "rc=$?"
  sleep 5
done
grep -H 'loaded from' $RAW/perf2_*.log
