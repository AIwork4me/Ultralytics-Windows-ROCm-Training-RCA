#!/usr/bin/env bash
# Round-3 evidence build: configure + build from pinned d4b574ac worktree C:/w58
# (clone of validated fin_mission/scripts/build_bfin.sh; only source/build dirs differ)
set -o pipefail
BTOOLS=/c/Users/rocm/Desktop/YOLO_AMD/phase3_buildtools
CMAKE_BIN=$BTOOLS/Lib/site-packages/cmake/data/bin
NINJA_BIN=$BTOOLS/Scripts
ROCMSDK=/c/Users/rocm/miniconda3/envs/yolo_amd/Lib/site-packages/_rocm_sdk_core
LLVM=$ROCMSDK/lib/llvm/bin
WINKIT="/c/Program Files (x86)/Windows Kits/10/bin/10.0.26100.0/x64"
STRIPPED=$(echo "$PATH" | tr ':' '\n' | grep -v "^/c/Users/rocm/miniconda3/" | paste -sd:)
export PATH="$CMAKE_BIN:$NINJA_BIN:$LLVM:$ROCMSDK/bin:$WINKIT:/c/Windows/System32:/c/Windows:$STRIPPED"
LOGDIR=/c/Users/rocm/Desktop/YOLO_AMD/r3_mission/build
mkdir -p "$LOGDIR"

echo "=== toolchain ===" | tee "$LOGDIR/toolchain.txt"
cmake --version | head -1 | tee -a "$LOGDIR/toolchain.txt"
ninja --version | tee -a "$LOGDIR/toolchain.txt"
"$LLVM/clang++.exe" --version | head -2 | tee -a "$LOGDIR/toolchain.txt"

# deps identical to 5.7 (sha256-verified then; reused from fin_mission/deps)
cmake -S C:/w58/projects/miopen -B C:/b58 -G Ninja \
  -DFETCHCONTENT_SOURCE_DIR_FRUGALLY_DEEP=C:/Users/rocm/Desktop/YOLO_AMD/fin_mission/deps/frugally-deep-0.15.31 \
  -DFETCHCONTENT_SOURCE_DIR_FUNCTIONALPLUS=C:/Users/rocm/Desktop/YOLO_AMD/fin_mission/deps/FunctionalPlus-0.2.25 \
  -DFETCHCONTENT_SOURCE_DIR_GTEST=C:/Users/rocm/Desktop/YOLO_AMD/fin_mission/deps/googletest-1.17.0 \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_C_COMPILER="C:/Users/rocm/miniconda3/envs/yolo_amd/Lib/site-packages/_rocm_sdk_core/lib/llvm/bin/clang.exe" \
  -DCMAKE_CXX_COMPILER="C:/Users/rocm/miniconda3/envs/yolo_amd/Lib/site-packages/_rocm_sdk_core/lib/llvm/bin/clang++.exe" \
  -DCMAKE_MAKE_PROGRAM="C:/Users/rocm/Desktop/YOLO_AMD/phase3_buildtools/Scripts/ninja.exe" \
  -DBUILD_DEV=OFF -DBUILD_TESTING=ON -DMIOPEN_TEST_ALL=ON -DMIOPEN_TEST_DISCRETE=ON \
  -DMIOPEN_BACKEND=HIP -DMIOPEN_USE_COMGR=ON \
  -DMIOPEN_BUILD_CK=OFF -DMIOPEN_BUILD_DRIVER=OFF \
  -DMIOPEN_USE_COMPOSABLEKERNEL=OFF -DMIOPEN_TEST_COMPOSABLEKERNEL=OFF \
  -DMIOPEN_ENABLE_AI_IMMED_MODE_FALLBACK=OFF -DMIOPEN_ENABLE_AI_KERNEL_TUNING=OFF \
  -DHALF_INCLUDE_DIR=C:/Users/rocm/Desktop/YOLO_AMD/phase3_deps/cmake_shims/include \
  -DROCRAND_INCLUDE_DIR=C:/Users/rocm/Desktop/YOLO_AMD/phase3_deps/stage_rocrand \
  -DUNZIPPER=C:/Users/rocm/Desktop/YOLO_AMD/phase3_deps/tools/bzip2.cmd \
  -DPython3_EXECUTABLE=C:/Users/rocm/miniconda3/python.exe \
  -DCMAKE_PREFIX_PATH="C:/Users/rocm/Desktop/YOLO_AMD/phase3_deps/dep_prefix/Library;C:/Users/rocm/Desktop/YOLO_AMD/phase3_deps/rocm-cmake;C:/Users/rocm/Desktop/YOLO_AMD/phase3_deps/cmake_shims/hip;C:/Users/rocm/Desktop/YOLO_AMD/phase3_deps/cmake_shims/hip-lang;C:/Users/rocm/Desktop/YOLO_AMD/phase3_deps/cmake_shims/rocblas;C:/Users/rocm/Desktop/YOLO_AMD/phase3_deps/cmake_shims/amd_comgr;C:/Users/rocm/Desktop/YOLO_AMD/phase3_deps/cmake_shims/hiprtc;C:/Users/rocm/Desktop/YOLO_AMD/phase3_deps/cmake_shims/rocrand;C:/Users/rocm/Desktop/YOLO_AMD/phase3_deps/cmake_shims/rocm-core;C:/Users/rocm/Desktop/YOLO_AMD/phase3_deps/cmake_shims/nlohmann_json" \
  > "$LOGDIR/configure_b58.log" 2>&1
RC=$?
echo "configure rc=$RC" >> "$LOGDIR/configure_b58.log"
if [ $RC -ne 0 ]; then tail -40 "$LOGDIR/configure_b58.log"; exit 1; fi

ninja -C /c/b58 MIOpen bin/test_hiprtc_selfcontained.exe bin/test_kthvalue.exe \
  > "$LOGDIR/build_b58.log" 2>&1
RC=$?
echo "build rc=$RC" >> "$LOGDIR/build_b58.log"
tail -5 "$LOGDIR/build_b58.log"
exit $RC
