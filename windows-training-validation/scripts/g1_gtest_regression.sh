#!/usr/bin/env bash
# G1.3 — HIPRTC no-STL regression via the historical gtest design (Round-3 B block).
# Runs the source-built gtest from its own build tree (b58m) so the loaded
# MIOpen.dll is the SAME patched binary (ed7c67a9) used in the Python legs.
# Two variants per fresh cache home:
#   (a) ambient includes (historical driver form)
#   (b) host STL hidden (VCToolsInstallDir redirect + empty INCLUDE)
# Exit codes are checked explicitly; logs archived raw.
set -u

B58M=/c/b58m
RAW="$(cd "$(dirname "$0")/../raw" && pwd)"
GTEST_FILTER="CPU_HipRtcSelfContained_NONE.*"
WHEEL_LIB="/c/Users/rocm/miniconda3/envs/pm13437_merged/Lib/site-packages/_rocm_sdk_libraries/bin"
WHEEL_CORE="/c/Users/rocm/miniconda3/envs/pm13437_merged/Lib/site-packages/_rocm_sdk_core/bin"
DEP_PREFIX="/c/Users/rocm/Desktop/YOLO_AMD/phase3_deps/dep_prefix/Library/bin"
WINKIT="/c/Program Files (x86)/Windows Kits/10/bin/10.0.26100.0/x64"

export PATH="$B58M/bin:$WHEEL_LIB:$WHEEL_CORE:$DEP_PREFIX:$WINKIT:/c/Windows/System32:/c/Windows:/usr/bin:$PATH"

for HOME_ID in gtest_nostl_r1 gtest_nostl_r2 gtest_nostl_r3; do
  CH="C:\\g1_home_${HOME_ID}"
  rm -rf "/c/g1_home_${HOME_ID}" && mkdir -p "/c/g1_home_${HOME_ID}"
  LOG="$RAW/${HOME_ID}.log"
  cd "$B58M"
  echo "=== $HOME_ID: ambient variant ===" > "$LOG"
  USERPROFILE="$CH" MIOPEN_LOG_LEVEL=6 ./bin/test_hiprtc_selfcontained.exe --gtest_filter="$GTEST_FILTER" >> "$LOG" 2>&1
  EXIT_AMBIENT=$?
  echo "ambient exit=$EXIT_AMBIENT" >> "$LOG"

  rm -rf "/c/g1_home_${HOME_ID}b" && mkdir -p "/c/g1_home_${HOME_ID}b"
  mkdir -p "/c/g1_home_${HOME_ID}b/fakevc"
  echo "=== $HOME_ID: no-STL variant ===" >> "$LOG"
  USERPROFILE="C:\\g1_home_${HOME_ID}b" MIOPEN_LOG_LEVEL=6 \
    VCToolsInstallDir="C:\\g1_home_${HOME_ID}b\\fakevc" INCLUDE="" \
    ./bin/test_hiprtc_selfcontained.exe --gtest_filter="$GTEST_FILTER" >> "$LOG" 2>&1
  EXIT_NOSTL=$?
  echo "nostl exit=$EXIT_NOSTL" >> "$LOG"

  echo "$HOME_ID: ambient_exit=$EXIT_AMBIENT nostl_exit=$EXIT_NOSTL passed=$(grep -cE '\[  PASSED  \] [0-9]+ tests?' "$LOG") compile_lines=$(grep -ciE 'hiprtc|Compiling' "$LOG")"
  if [ "$EXIT_AMBIENT" -ne 0 ] || [ "$EXIT_NOSTL" -ne 0 ]; then
    echo "$HOME_ID: FAIL (see $LOG)"; exit 1
  fi
done
echo "GTEST_REGRESSION: PASS (3 independent fresh-cache-home runs, ambient + no-STL)"
