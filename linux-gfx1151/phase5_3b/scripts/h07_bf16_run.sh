#!/usr/bin/env bash
# H07 BF16 kthvalue runner — the exact wrapper invocation used for the
# recorded evidence (logs/h07_bf16_leg{A,B}.log). Added post-panel per
# Reviewer B's note so the probe is reproducible from a checked-in script.
# Build first:
#   $SP/_rocm_sdk_devel/lib/llvm/bin/amdclang++ -O2 -std=c++17 \
#     -D__HIP_PLATFORM_AMD__=1 -DHIP_PLATFORM=amd \
#     -I <legB-test build>/include -I src/legB/projects/miopen/include \
#     -I <SP>/_rocm_sdk_devel/include -I <SP>/_rocm_sdk_core/include \
#     scripts/bf16_kthvalue_probe.cpp -o tmp/bf16_probe -ldl
set -euo pipefail
WS=/home/amd/Desktop/YOLO_AMD/phase5_3b
SP=/home/amd/Desktop/YOLO_AMD/.venv/lib/python3.13/site-packages
for leg in legA legB; do
  FRESH="$WS/tmp/fresh_cache/h07_bf16_$leg"
  rm -rf "$FRESH"; mkdir -p "$FRESH/xdg"
  LD_PRELOAD="$WS/installs/$leg/lib/libMIOpen.so.1" \
  LD_LIBRARY_PATH="$SP/_rocm_sdk_core/lib:$SP/_rocm_sdk_libraries/lib:$SP/_rocm_sdk_devel/lib:/home/amd/Desktop/YOLO_AMD/.deps/miopen/lib" \
  MIOPEN_CUSTOM_CACHE_DIR="$FRESH" XDG_CACHE_HOME="$FRESH/xdg" MIOPEN_LOG_LEVEL=5 \
  "$WS/tmp/bf16_probe" > "$WS/logs/h07_bf16_$leg.log" 2>&1
  echo "$leg exit=$?"
  grep -E 'BF16_RESULT|value_mismatches' "$WS/logs/h07_bf16_$leg.log"
done
