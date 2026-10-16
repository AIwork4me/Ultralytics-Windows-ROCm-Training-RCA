#!/usr/bin/env bash
# Round-3 positive runs from fresh pinned build C:/b58 (source d4b574ac).
# B: hiprtc regression gtest (fresh MIOpen cache via redirected USERPROFILE)
# E: kthvalue 27-case gtest (fresh cache; a second warm run follows for perf)
set -o pipefail
WHEEL_LIB=/c/Users/rocm/miniconda3/envs/yolo_amd/Lib/site-packages/_rocm_sdk_libraries/bin
WHEEL_CORE=/c/Users/rocm/miniconda3/envs/yolo_amd/Lib/site-packages/_rocm_sdk_core/bin
WINKIT="/c/Program Files (x86)/Windows Kits/10/bin/10.0.26100.0/x64"
DEP_PREFIX=/c/Users/rocm/Desktop/YOLO_AMD/phase3_deps/dep_prefix/Library/bin
export PATH="/c/b58/bin:$WHEEL_LIB:$WHEEL_CORE:$DEP_PREFIX:$WINKIT:/c/Windows/System32:/c/Windows:/usr/bin:$PATH"
RAW=/c/Users/rocm/Desktop/YOLO_AMD/r3_mission/raw

echo "=== binary hashes (Round-3 pinned build @ d4b574ac) ==="
sha256sum /c/b58/bin/MIOpen.dll /c/b58/bin/test_hiprtc_selfcontained.exe /c/b58/bin/test_kthvalue.exe \
  | tee /c/Users/rocm/Desktop/YOLO_AMD/r3_mission/provenance/binary_sha256_b58.txt

cd /c/b58

echo "=== B: hiprtc regression gtest (fresh cache home) ==="
rm -rf /c/r3home_b && mkdir -p /c/r3home_b
USERPROFILE='C:\r3home_b' MIOPEN_LOG_LEVEL=6 ./bin/test_hiprtc_selfcontained.exe --gtest_filter=CPU_HipRtcSelfContained_NONE.* \
  > "$RAW/hiprtc/B_r3_gtest_run.log" 2>&1
echo "B exit=$?"
tail -4 "$RAW/hiprtc/B_r3_gtest_run.log"
grep -c "Compiling\|hipRTC" "$RAW/hiprtc/B_r3_gtest_run.log" || true
grep -o "3\.6\.2\.[0-9a-f-]*" "$RAW/hiprtc/B_r3_gtest_run.log" | sort -u || true

echo "=== E: kthvalue cold (fresh cache home) ==="
rm -rf /c/r3home_e1 && mkdir -p /c/r3home_e1
/usr/bin/time -p env USERPROFILE='C:\r3home_e1' ./bin/test_kthvalue.exe \
  > "$RAW/kthvalue/E_r3_kthvalue_cold.log" 2>"$RAW/kthvalue/E_r3_kthvalue_cold.time"
echo "E-cold exit=$?"
tail -3 "$RAW/kthvalue/E_r3_kthvalue_cold.log"
grep -o "[0-9]* ms" "$RAW/kthvalue/E_r3_kthvalue_cold.log" | tail -1

echo "=== E: kthvalue warm (same home, second run) ==="
USERPROFILE='C:\r3home_e1' ./bin/test_kthvalue.exe \
  > "$RAW/kthvalue/E_r3_kthvalue_warm.log" 2>&1
echo "E-warm exit=$?"
tail -3 "$RAW/kthvalue/E_r3_kthvalue_warm.log"
