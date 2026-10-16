#!/usr/bin/env bash
# Round-3 negative control (C): pristine unpatched build C:/bwp (b8cf0e7b)
# rerun with fresh cache home. Expected: FAILED with the exact original
# signature  fatal error: 'type_traits' file not found  (this is the pass
# condition for the control; exit code will be non-zero).
set -o pipefail
WHEEL_LIB=/c/Users/rocm/miniconda3/envs/yolo_amd/Lib/site-packages/_rocm_sdk_libraries/bin
WHEEL_CORE=/c/Users/rocm/miniconda3/envs/yolo_amd/Lib/site-packages/_rocm_sdk_core/bin
WINKIT="/c/Program Files (x86)/Windows Kits/10/bin/10.0.26100.0/x64"
DEP_PREFIX=/c/Users/rocm/Desktop/YOLO_AMD/phase3_deps/dep_prefix/Library/bin
export PATH="/c/bwp/bin:$WHEEL_LIB:$WHEEL_CORE:$DEP_PREFIX:$WINKIT:/c/Windows/System32:/c/Windows:/usr/bin:$PATH"
RAW=/c/Users/rocm/Desktop/YOLO_AMD/r3_mission/raw/negative_control

cd /c/bwp
rm -rf /c/r3home_c && mkdir -p /c/r3home_c
USERPROFILE='C:\r3home_c' MIOPEN_LOG_LEVEL=6 ./bin/test_hiprtc_selfcontained.exe --gtest_filter=CPU_HipRtcSelfContained_NONE.RtCompilesInlineKernelWithoutHostStl \
  > "$RAW/C_r3_pristine_run.log" 2>&1
RC=$?
echo "C exit=$RC (expected non-zero)"
grep -n "fatal error" "$RAW/C_r3_pristine_run.log" || echo "SIGNATURE NOT FOUND"
grep -o "3\.6\.2\.[0-9a-f-]*" "$RAW/C_r3_pristine_run.log" | sort -u
tail -5 "$RAW/C_r3_pristine_run.log"
