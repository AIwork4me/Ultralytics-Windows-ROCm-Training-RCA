#!/usr/bin/env bash
# Parameterized MIOpen leg builder — IDENTICAL flags for both A/B legs.
# Env overrides: MIOPEN_SOURCE, MIOPEN_BUILD, MIOPEN_INSTALL, MIOPEN_ARCH,
# MIOPEN_JOBS. Defaults = leg A (baseline).
set -euo pipefail

WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$WS/scripts/env_rocm7141.sh" >/dev/null

SRC="${MIOPEN_SOURCE:-$WS/source/upstream-pristine/projects/miopen}"
BLD="${MIOPEN_BUILD:-$WS/build/baseline-miopen}"
INST="${MIOPEN_INSTALL:-$WS/install/baseline}"
SP="$WS/tools/rocm7141-venv/lib/python3.12/site-packages"
DEVEL="$SP/_rocm_sdk_devel"
CORE="$SP/_rocm_sdk_core"
LIBS="$SP/_rocm_sdk_libraries"
CXX="$DEVEL/llvm/bin/amdclang++"

ARCH="${MIOPEN_ARCH:-gfx1100}"
JOBS="${MIOPEN_JOBS:-$(nproc)}"

mkdir -p "$BLD" "$INST"
cd "$BLD"

cmake -G Ninja "$SRC" \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_INSTALL_PREFIX="$INST" \
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
  -DBUILD_TESTING=OFF \
  -DCMAKE_INSTALL_LIBDIR=lib \
  2>&1 | tee "$WS/logs/$(basename "$BLD")_configure.log"

echo "=== CMakeCache contamination check (/opt/rocm) ==="
if grep -n "opt/rocm" CMakeCache.txt; then
  echo "FATAL: /opt/rocm found in CMakeCache.txt" >&2
  exit 3
fi
echo "CACHE_CLEAN"

cmake --build . -j "$JOBS" 2>&1 | tee "$WS/logs/$(basename "$BLD")_build.log"
cmake --install . 2>&1 | tee "$WS/logs/$(basename "$BLD")_install.log"

echo "=== result ==="
ls -la "$INST/lib/"
sha256sum "$INST/lib/libMIOpen.so.1"*
