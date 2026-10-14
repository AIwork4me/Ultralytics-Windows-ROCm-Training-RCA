#!/usr/bin/env bash
# Post-build runs: B (hiprtc positive) + E (kthvalue) from the fresh pinned build.
set -o pipefail
RAW=/c/Users/rocm/Desktop/YOLO_AMD/fin_mission/raw
WHEEL_LIB=/c/Users/rocm/miniconda3/envs/yolo_amd/Lib/site-packages/_rocm_sdk_libraries/bin
WHEEL_CORE=/c/Users/rocm/miniconda3/envs/yolo_amd/Lib/site-packages/_rocm_sdk_core/bin
WINKIT="/c/Program Files (x86)/Windows Kits/10/bin/10.0.26100.0/x64"
DEP_PREFIX=/c/Users/rocm/Desktop/YOLO_AMD/phase3_deps/dep_prefix/Library/bin
export PATH="/c/bfin/bin:$WHEEL_LIB:$WHEEL_CORE:$DEP_PREFIX:$WINKIT:/c/Windows/System32:/c/Windows:/usr/bin:$PATH"

echo "=== binary hashes (fresh pinned build @ f0f330c4) ==="
sha256sum /c/bfin/bin/MIOpen.dll /c/bfin/bin/test_hiprtc_selfcontained.exe /c/bfin/bin/test_kthvalue.exe \
  | tee "$RAW/../provenance/binary_sha256.txt"

cd /c/bfin

echo "=== B: hiprtc regression gtest (positive, patched) ==="
MIOPEN_LOG_LEVEL=6 ./bin/test_hiprtc_selfcontained.exe --gtest_filter=CPU_HipRtcSelfContained_NONE.* \
  > "$RAW/hiprtc/B_final_gtest_run.log" 2>&1
echo "B exit=$?"
tail -4 "$RAW/hiprtc/B_final_gtest_run.log"

echo "=== E: kthvalue ==="
./bin/test_kthvalue.exe > "$RAW/kthvalue/E_kthvalue_patched.log" 2>&1
echo "E exit=$?"
tail -3 "$RAW/kthvalue/E_kthvalue_patched.log"
