#!/usr/bin/env bash
# Gate H04 — two independent source-built MIOpen legs from the frozen base.
# LEG A: pristine upstream (legA worktree).
# LEG B: exact R2-patched source (legB worktree, tree b983cadd).
# Single-variable discipline: same wheel 7.14 toolchain, same compiler,
# same gfx1151 target, same build type, same HIPRTC/COMGR config, same
# CMake options; separate CMake caches, install prefixes, runtime caches.
# Recipe = Phase-3 proven configuration (BUILD_TESTING=OFF this time;
# the H03 test build is separate).
set -euo pipefail
WS=/home/amd/Desktop/YOLO_AMD/phase5_3b
SP=/home/amd/Desktop/YOLO_AMD/.venv/lib/python3.13/site-packages
DEVEL="$SP/_rocm_sdk_devel"; CORE="$SP/_rocm_sdk_core"; LIBS="$SP/_rocm_sdk_libraries"
CXX="$DEVEL/lib/llvm/bin/amdclang++"
ARCH=gfx1151
export PATH="/home/amd/Desktop/YOLO_AMD/.venv/bin:$PATH"
LEG="$1"   # legA | legB
SRCWT="$WS/src/$LEG"
SRCDIR="$SRCWT/projects/miopen"
BLD="$WS/builds/$LEG"
INST="$WS/installs/$LEG"

case "$LEG" in
  legA) EXPECT_TREE=8b0bf035e4568a1d994512b4346fed0dde3c591b ;;
  legB) EXPECT_TREE=b983caddf9f9f561e7d1b590deadb16267c2de15 ;;
  *) echo "usage: $0 legA|legB" >&2; exit 2 ;;
esac

TREE_SHA=$(git -C "$SRCWT" rev-parse 'HEAD^{tree}')
[ "$TREE_SHA" = "$EXPECT_TREE" ] || { echo "FATAL: $LEG tree $TREE_SHA != $EXPECT_TREE" >&2; exit 3; }
[ -z "$(git -C "$SRCWT" status --porcelain)" ] || { echo "FATAL: $LEG worktree dirty" >&2; exit 3; }
echo "[H04] $LEG source verified: tree $TREE_SHA"

mkdir -p "$BLD" && cd "$BLD"
cmake -G Ninja "$SRCDIR" \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_INSTALL_PREFIX="$INST" \
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
  -DBUILD_TESTING=OFF \
  -DCMAKE_INSTALL_LIBDIR=lib \
  -DFETCHCONTENT_SOURCE_DIR_FUNCTIONALPLUS="$WS/builds/legB-test/_deps/functionalplus-src" \
  -DFETCHCONTENT_SOURCE_DIR_FRUGALLY-DEEP="$WS/builds/legB-test/_deps/frugally-deep-src" \
  -DFETCHCONTENT_SOURCE_DIR_GTEST="$WS/builds/legB-test/_deps/gtest-src" \
  2>&1 | tee "$WS/logs/h04_configure_$LEG.log" | tail -4

if grep -q "opt/rocm" CMakeCache.txt; then
  echo "FATAL: /opt/rocm contamination in $LEG CMakeCache" >&2
  grep "opt/rocm" CMakeCache.txt | head
  exit 3
fi
echo "[H04] $LEG CACHE_CLEAN"

cmake --build . 2>&1 | tee "$WS/logs/h04_build_$LEG.log" | tail -3
cmake --install . 2>&1 | tee "$WS/logs/h04_install_$LEG.log" | tail -2
LIB="$INST/lib/libMIOpen.so.1"
[ -f "$LIB" ] || { echo "FATAL: $LIB missing" >&2; exit 4; }
sha256sum "$INST/lib/libMIOpen.so.1.0"
ldd "$INST/lib/libMIOpen.so.1.0" | grep -E 'miopen|hip|sqlite' | head -8
echo "[H04] $LEG DONE"
