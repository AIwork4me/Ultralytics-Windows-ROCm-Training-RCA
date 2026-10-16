#!/usr/bin/env bash
# Phase-5 cold-compile A/B: gtest (5 RTC compiles incl. probes) and kthvalue
# (runtime-compiled radix kernels), fresh cache home per leg, wall-clock timed.
set -o pipefail
WHEEL_LIB=/c/Users/rocm/miniconda3/envs/yolo_amd/Lib/site-packages/_rocm_sdk_libraries/bin
WHEEL_CORE=/c/Users/rocm/miniconda3/envs/yolo_amd/Lib/site-packages/_rocm_sdk_core/bin
WINKIT="/c/Program Files (x86)/Windows Kits/10/bin/10.0.26100.0/x64"
DEP_PREFIX=/c/Users/rocm/Desktop/YOLO_AMD/phase3_deps/dep_prefix/Library/bin
RAW=/c/Users/rocm/Desktop/YOLO_AMD/r3_mission/raw/perf
mkdir -p "$RAW"

run_leg() { # $1=label $2=bindir $3=home
  local L=$1 BD=$2 HOME_DIR=$3
  export PATH="$BD/bin:$WHEEL_LIB:$WHEEL_CORE:$DEP_PREFIX:$WINKIT:/c/Windows/System32:/c/Windows:/usr/bin:$PATH"
  cd "$BD"
  rm -rf "$HOME_DIR" && mkdir -p "$HOME_DIR"
  local T0 T1
  # cold gtest (fresh home)
  T0=$(date +%s.%N)
  USERPROFILE="C:\\$(basename $HOME_DIR)" ./bin/test_hiprtc_selfcontained.exe --gtest_filter=CPU_HipRtcSelfContained_NONE.RtCompilesInlineKernelWithoutHostStl > "$RAW/cold_gtest_$L.log" 2>&1
  RC1=$?
  T1=$(date +%s.%N); echo "cold_gtest_$L rc=$RC1 wall_s=$(echo "$T1 $T0" | awk '{printf "%.2f", $1-$2}')" | tee -a "$RAW/cold_timings.txt"
  # cold kthvalue (fresh home)
  rm -rf "$HOME_DIR" && mkdir -p "$HOME_DIR"
  T0=$(date +%s.%N)
  USERPROFILE="C:\\$(basename $HOME_DIR)" ./bin/test_kthvalue.exe > "$RAW/cold_kthvalue_$L.log" 2>&1
  RC2=$?
  T1=$(date +%s.%N); echo "cold_kthvalue_$L rc=$RC2 wall_s=$(echo "$T1 $T0" | awk '{printf "%.2f", $1-$2}')" | tee -a "$RAW/cold_timings.txt"
  # warm kthvalue (same home)
  T0=$(date +%s.%N)
  USERPROFILE="C:\\$(basename $HOME_DIR)" ./bin/test_kthvalue.exe > "$RAW/warm_kthvalue_$L.log" 2>&1
  RC3=$?
  T1=$(date +%s.%N); echo "warm_kthvalue_$L rc=$RC3 wall_s=$(echo "$T1 $T0" | awk '{printf "%.2f", $1-$2}')" | tee -a "$RAW/cold_timings.txt"
  # keep cache home for blob comparison
  cp -r "$HOME_DIR/.miopen" "$RAW/kern_cache_$L" 2>/dev/null || true
}

echo "=== cold/warm A/B timing ($(date -u +%Y-%m-%dT%H:%M:%SZ)) ===" | tee "$RAW/cold_timings.txt"
run_leg A /c/bfin /c/r3home_A
run_leg B /c/b58  /c/r3home_B
run_leg A /c/bfin /c/r3home_A2
run_leg B /c/b58  /c/r3home_B2
cat "$RAW/cold_timings.txt"
