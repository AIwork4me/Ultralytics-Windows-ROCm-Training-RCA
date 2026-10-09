#!/usr/bin/env bash
# Phase 5.3 Gate L07 — R2 CTest portability build.
# SINGLE-VARIABLE discipline: identical flags to the Phase-5.2.1 Gate-C2
# measurement build EXCEPT:
#   - source = R2 patched tree (b983cadd) instead of R1 tree (605d0d21)
#   - NO CMAKE_CXX_STANDARD_INCLUDE_DIRECTORIES workaround
#   - NO CMAKE_EXE_LINKER_FLAGS workaround
# The R2 patch (F-C2-2 fix: capability-aware hiprtc::hiprtc link) must make
# the target build cleanly WITHOUT any manual include/lib-directory flags.
set -euo pipefail
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # miopen-w7900-validation
source "$WS/scripts/env_rocm7141.sh" >/dev/null

SRC="$WS/source/final-patched/projects/miopen"
BLD="$WS/build/recon53-test"
LOGS="$WS/phase5_3/logs"
mkdir -p "$BLD" "$LOGS"

# Guard: R2 patched tree identity.
TREE_SHA="$(git -C "$WS/source/final-patched" rev-parse HEAD^{tree})"
[ "$TREE_SHA" = "b983caddf9f9f561e7d1b590deadb16267c2de15" ] \
  || { echo "FATAL: R2 tree identity mismatch: $TREE_SHA" >&2; exit 3; }

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
  2>&1 | tee "$LOGS/L07_ctest_build.log"
# NOTE: deliberately NO -DCMAKE_CXX_STANDARD_INCLUDE_DIRECTORIES and NO
# -DCMAKE_EXE_LINKER_FLAGS. R2 must build without them (mission L07).

if grep -n "opt/rocm" CMakeCache.txt; then
  echo "FATAL: /opt/rocm found in CMakeCache.txt" >&2; exit 3
fi
echo "CACHE_CLEAN"

cmake --build . --target test_hiprtc_selfcontained 2>&1 | tee -a "$LOGS/L07_ctest_build.log"
echo "BUILD_OK_NO_WORKAROUNDS"
