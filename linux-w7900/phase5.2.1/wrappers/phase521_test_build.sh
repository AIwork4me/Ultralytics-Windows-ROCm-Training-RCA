#!/usr/bin/env bash
# Phase 5.2.1 Gate C2 — isolated BUILD_TESTING=ON test build for the frozen
# patched MIOpen tree (worktree at refs/phase52/frozen-base + P5.1 series,
# tree SHA 605d0d214acdbc06086fdb27c61fec970c0f2798 verified before use).
#
# SINGLE-VARIABLE discipline: flags are IDENTICAL to build_leg_miopen.sh
# (Leg A) except -DBUILD_TESTING=ON and a separate build dir; the goal is
# CTest discovery + exit-code audit of test_hiprtc_selfcontained, NOT a
# second operational leg. No install. No GPU execution.
set -euo pipefail

WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # miopen-w7900-validation
source "$WS/scripts/env_rocm7141.sh" >/dev/null

SRC="${MIOPEN_SOURCE:-$WS/build/recon/phase521-test-tree/projects/miopen}"
BLD="${MIOPEN_BUILD:-$WS/build/test-BUILD_TESTING-ON}"
LOGS="$WS/repos/rca-evidence/linux-w7900/phase5.2.1/logs"
mkdir -p "$BLD" "$LOGS"

# Guard: patched tree identity (must equal the frozen reconstructed tree).
TREE_SHA="$(git -C "$WS/build/recon/phase521-test-tree" add -A 2>/dev/null; git -C "$WS/build/recon/phase521-test-tree" write-tree)"
[ "$TREE_SHA" = "605d0d214acdbc06086fdb27c61fec970c0f2798" ] \
  || { echo "FATAL: patched tree identity mismatch: $TREE_SHA" >&2; exit 3; }

SP="$WS/tools/rocm7141-venv/lib/python3.12/site-packages"
DEVEL="$SP/_rocm_sdk_devel"; CORE="$SP/_rocm_sdk_core"; LIBS="$SP/_rocm_sdk_libraries"
CXX="$DEVEL/llvm/bin/amdclang++"
ARCH=gfx1100

cd "$BLD"
cmake -G Ninja "$SRC" \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_INSTALL_PREFIX="$BLD/install-unused" \
  -DCMAKE_CXX_COMPILER="$CXX" \
  -DCMAKE_PREFIX_PATH="$DEVEL;$CORE;$LIBS;$LIBS/lib" \
  -Dhip_DIR="$DEVEL/lib/cmake/hip" \
  -Dhiprtc_DIR="$DEVEL/lib/cmake/hiprtc" \
  -Drocblas_DIR="$LIBS/lib/cmake/rocblas" \
  -Dhipblaslt_DIR="$DEVEL/lib/cmake/hipblaslt" \
  -Dhipblas-common_DIR="$DEVEL/lib/cmake/hipblas-common" \
  -Damd_comgr_DIR="$CORE/lib/cmake/amd_comgr" \
  -Drocrand_DIR="$DEVEL/lib/cmake/rocrand" \
  -DEigen3_DIR="/usr/share/eigen3/cmake" \
  -DMIOPEN_OFFLOADBUNDLER_BIN="$DEVEL/llvm/bin/clang-offload-bundler" \
  -DMIOPEN_AMDGCN_ASSEMBLER="$DEVEL/llvm/bin/clang" \
  -DFETCHCONTENT_SOURCE_DIR_FUNCTIONALPLUS="$WS/build/thirdparty-preseed/functionalplus" \
  -D'FETCHCONTENT_SOURCE_DIR_FRUGALLY-DEEP='"$WS/build/thirdparty-preseed/frugally-deep" \
  -DFETCHCONTENT_SOURCE_DIR_GTEST="$WS/build/thirdparty-preseed/googletest" \
  -DMIOPEN_BACKEND=HIP \
  -DMIOPEN_USE_HIPRTC=ON \
  -DMIOPEN_USE_COMGR=ON \
  -DMIOPEN_USE_COMPOSABLEKERNEL=OFF \
  -DGPU_TARGETS="$ARCH" \
  -DAMDGPU_TARGETS="$ARCH" \
  -DBUILD_TESTING=ON \
  -DCMAKE_INSTALL_LIBDIR=lib \
  -DCMAKE_CXX_STANDARD_INCLUDE_DIRECTORIES="$DEVEL/include" \
  -DCMAKE_EXE_LINKER_FLAGS="-L$DEVEL/lib" \
  2>&1 | tee "$LOGS/C2_test_build_configure.log"
# ^ HARNESS WORKAROUNDS (build-tree only; frozen patch 0003 NOT modified):
#   (1) the hiprtc CMake package exports ONLY the namespaced hiprtc::hiprtc
#   target (INTERFACE_INCLUDE_DIRECTORIES .../include); patch 0003 links
#   the plain name `hiprtc` on non-WIN32, which carries no usage
#   requirements, so <hip/hiprtc.h> is not findable at compile time on
#   Linux. CMAKE_CXX_STANDARD_INCLUDE_DIRECTORIES appends the SDK include
#   dir for this isolated measurement build only.
#   (2) the plain-name link `-lhiprtc` also gets no -L for the SDK lib dir
#   (no other linked target supplies it here, unlike MIOpen's impl target
#   which also links hip::device/host); CMAKE_EXE_LINKER_FLAGS supplies it.
#   Both recorded as Gate-C2 finding F-C2-2 (CI portability defect in
#   frozen patch 0003).

echo "=== CMakeCache contamination check (/opt/rocm) ==="
if grep -n "opt/rocm" CMakeCache.txt; then
  echo "FATAL: /opt/rocm found in CMakeCache.txt" >&2; exit 3
fi
echo "CACHE_CLEAN"
grep -E "^BUILD_TESTING:|^MIOPEN_USE_HIPRTC:|^GPU_TARGETS:|^CMAKE_CXX_COMPILER:" CMakeCache.txt \
  | tee "$LOGS/C2_test_build_cache_facts.txt"

# Build ONLY the patch-0003 test target.
cmake --build . --target test_hiprtc_selfcontained 2>&1 | tee "$LOGS/C2_test_build_build.log"

echo "=== CTest discovery ==="
ctest -N -R test_hiprtc_selfcontained 2>&1 | tee "$LOGS/C2_ctest_discovery.log"

echo "=== CTest run (unamended registration; exit code recorded) ==="
set +e
ctest -R '^test_hiprtc_selfcontained$' --output-on-failure 2>&1 | tee "$LOGS/C2_ctest_run.log"
ctest_rc=${PIPESTATUS[0]}
set -e
echo "CTEST_EXIT_CODE=$ctest_rc" | tee -a "$LOGS/C2_ctest_run.log"

TESTBIN="$(find "$BLD" -name test_hiprtc_selfcontained -type f -executable | head -1)"
echo "TESTBIN=$TESTBIN"
KDIR="$WS/build/recon/phase521-test-tree/projects/miopen/src/kernels"

echo "=== Direct mode matrix ==="
for mode in positive with-stl ordinary negative; do
  set +e
  "$TESTBIN" "$KDIR" --mode=$mode --arch=gfx1100 \
    > "$LOGS/C2_direct_mode_${mode}.log" 2>&1
  rc=$?
  set -e
  echo "MODE=$mode EXIT=$rc" | tee -a "$LOGS/C2_direct_mode_${mode}.log"
done

echo "=== Header availability under -nostdinc (patch's own probe, from C2 positive log) ==="
grep -E "STL_PROBE|INCONCLUSIVE|reachable" "$LOGS/C2_direct_mode_positive.log" || true
echo "DONE"
