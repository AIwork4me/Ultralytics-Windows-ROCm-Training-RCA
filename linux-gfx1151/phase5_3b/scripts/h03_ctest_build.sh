#!/usr/bin/env bash
# Gate H03 — targeted R2 CTest validation on Linux gfx1151.
# Configure a BUILD_TESTING=ON test build from the EXACT R2 source
# (legB, tree b983cadd), wheel 7.14 toolchain, MIOPEN_USE_HIPRTC=ON,
# GPU_TARGETS=gfx1151. NO manual HIPRTC include/lib injection — the R2
# CMake portability fix must carry the build by itself (single-variable
# discipline vs the Phase-3/W7900 recipes).
set -euo pipefail
WS=/home/amd/Desktop/YOLO_AMD/phase5_3b
SRC="$WS/src/legB/projects/miopen"
BLD="$WS/builds/legB-test"
SP=/home/amd/Desktop/YOLO_AMD/.venv/lib/python3.13/site-packages
DEVEL="$SP/_rocm_sdk_devel"; CORE="$SP/_rocm_sdk_core"; LIBS="$SP/_rocm_sdk_libraries"
CXX="$DEVEL/lib/llvm/bin/amdclang++"
ARCH=gfx1151
export PATH="/home/amd/Desktop/YOLO_AMD/.venv/bin:$PATH"   # ninja 1.13.2 (wheel venv)

# Guard: exact R2 source identity
TREE_SHA=$(git -C "$WS/src/legB" rev-parse 'HEAD^{tree}')
[ "$TREE_SHA" = "b983caddf9f9f561e7d1b590deadb16267c2de15" ] \
  || { echo "FATAL: legB tree mismatch: $TREE_SHA" >&2; exit 3; }
echo "[H03] source tree OK: $TREE_SHA"

mkdir -p "$BLD" && cd "$BLD"
cmake -G Ninja "$SRC" \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_INSTALL_PREFIX="$BLD/install-unused" \
  -DCMAKE_CXX_COMPILER="$CXX" \
  -DCMAKE_PREFIX_PATH="$DEVEL;$CORE;$LIBS;$LIBS/lib;/home/amd/Desktop/YOLO_AMD/.deps/miopen" \
  -Dhip_DIR="$DEVEL/lib/cmake/hip" \
  -Dhiprtc_DIR="$DEVEL/lib/cmake/hiprtc" \
  -Drocblas_DIR="$DEVEL/lib/cmake/rocblas" \
  -Dhipblaslt_DIR="$DEVEL/lib/cmake/hipblaslt" \
  -Damd_comgr_DIR="$DEVEL/lib/cmake/amd_comgr" \
  -DMIOPEN_OFFLOADBUNDLER_BIN="$DEVEL/llvm/bin/clang-offload-bundler" \
  -DMIOPEN_AMDGCN_ASSEMBLER="$DEVEL/llvm/bin/clang" \
  -DMIOPEN_BACKEND=HIP \
  -DMIOPEN_USE_HIPRTC=ON \
  -DMIOPEN_USE_COMGR=ON \
  -DMIOPEN_USE_COMPOSABLEKERNEL=OFF \
  -DGPU_TARGETS="$ARCH" -DAMDGPU_TARGETS="$ARCH" \
  -DBUILD_TESTING=ON \
  -DCMAKE_INSTALL_LIBDIR=lib \
  2>&1 | tee "$WS/logs/h03_configure.log" | tail -5

if grep -q "opt/rocm" CMakeCache.txt; then
  echo "FATAL: /opt/rocm contamination in CMakeCache.txt" >&2
  grep "opt/rocm" CMakeCache.txt | head -5
  exit 3
fi
echo "[H03] CACHE_CLEAN (no /opt/rocm references)"

cmake --build . --target test_hiprtc_selfcontained 2>&1 | tee "$WS/logs/h03_build.log" | tail -5
echo "[H03] BUILD_OK_NO_WORKAROUNDS"

BIN="$BLD/bin/test_hiprtc_selfcontained"
sha256sum "$BIN" | tee "$WS/evidence/h03_target_sha256.txt"
ctest -N -R '^test_hiprtc_selfcontained$' 2>&1 | tee "$WS/logs/h03_ctest_N.log"
echo "[H03] configured+built"
