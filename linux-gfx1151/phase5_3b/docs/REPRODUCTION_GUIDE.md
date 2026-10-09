# REPRODUCTION GUIDE — Phase 5.3B (Linux gfx1151 R2 cross-OS validation)

Machine profile: AMD Radeon 8060S (gfx1151), Ubuntu 24.04.4, wheel ROCm
7.14.0 SDK isolated inside a venv (torch 2.12.0+rocm7.14.0), system ROCm
7.2.1 coexisting but excluded from every configure/runtime path.

## 0. Workspace

```bash
WS=/home/amd/Desktop/YOLO_AMD/phase5_3b      # scripts/, logs/, evidence/, src/, builds/, installs/
RCA=/home/amd/Desktop/YOLO_AMD/Ultralytics-Windows-ROCm-Training-RCA
```

## 1. R2 evidence integrity (H01)

```bash
git -C $RCA fetch origin
git clone $RCA $WS/tmp/r2-evidence-clone
git -C $WS/tmp/r2-evidence-clone checkout --detach c8417161125dc33275b7ac615298b449a81e7cf8
cd $WS/tmp/r2-evidence-clone/patches/phase5_1_r2/canonical
sha256sum 0001-*.patch 0002-*.patch 0003-*.patch     # 816946b4…, 46044d8c…, df7c3c3a…
cat 0001-*.patch 0002-*.patch 0003-*.patch | sha256sum  # 48308f6d…
python3 $WS/scripts/check_final_handoff_r2.py --check-only \
  $WS/tmp/r2-evidence-clone/findings/phase5_1_r2/FINAL_HANDOFF.json \
  --rca-root $WS/tmp/r2-evidence-clone \
  --rca-evidence-sha c8417161125dc33275b7ac615298b449a81e7cf8 \
  --git-repo $WS/src/upstream.git        # VERDICT PASS
python3 $WS/scripts/run_h01_adversarial_matrix.py   # negative controls must FAIL
```

## 2. Source acquisition (blob backfill, flaky-network safe)

```bash
cd $WS/src && git init upstream.git && cd upstream.git
git remote add origin https://github.com/ROCm/rocm-libraries.git
git config remote.origin.promisor true
git config remote.origin.partialclonefilter blob:none
git fetch --depth=1 origin 7c5866144ac4b879be442563e2b49fa1c142ea36
# backfill blobs (raw.githubusercontent, SHA-1-verified per blob):
$WS/scripts/raw_backfill_checkout.sh $WS/src/upstream.git \
  7c5866144ac4b879be442563e2b49fa1c142ea36 projects/miopen
# shared/ctest needed for BUILD_TESTING=ON (H03): see scripts/h03_shared_lean_fetch.py pattern
```

## 3. Two-method reconstruction (H02)

```bash
$WS/scripts/h02_reconstruct.sh    # legA pristine; legB git am; M2 git apply --index + write-tree
# expect: METHOD 1 and METHOD 2 both -> tree b983caddf9f9f561e7d1b590deadb16267c2de15
```

## 4. Legs (H04; recipe = Phase-3 proven config)

```bash
$WS/scripts/h04_build_legs.sh legA    # installs/legA  lib sha 7f282a6f…
$WS/scripts/h04_build_legs.sh legB    # installs/legB  lib sha b14e907a…
```

Key CMake semantics: `MIOPEN_BACKEND=HIP MIOPEN_USE_HIPRTC=ON
MIOPEN_USE_COMGR=ON MIOPEN_USE_COMPOSABLEKERNEL=OFF GPU_TARGETS=gfx1151
BUILD_TESTING=OFF CMAKE_BUILD_TYPE=RelWithDebInfo`, wheel amdclang++,
explicit wheel cache pins (hip_DIR/hiprtc_DIR/rocblas_DIR/hipblaslt_DIR/
amd_comgr_DIR), identical FETCHCONTENT preseeds for both legs.

## 5. CTest portability (H03)

```bash
$WS/scripts/h03_ctest_build.sh          # BUILD_TESTING=ON build of test_hiprtc_selfcontained
cd $WS/builds/legB-test
ctest -N -R '^test_hiprtc_selfcontained$'
ctest --output-on-failure -R '^test_hiprtc_selfcontained$'   # Skipped (exit 4 -> SKIP_RETURN_CODE)
MIOPEN_USER_DB_PATH=$PWD/test bin/test_hiprtc_selfcontained ../src/legB/projects/miopen/src/kernels --arch=gfx1151            # exit 4 INCONCLUSIVE
MIOPEN_USER_DB_PATH=$PWD/test bin/test_hiprtc_selfcontained … --mode=ordinary   # exit 0
MIOPEN_USER_DB_PATH=$PWD/test bin/test_hiprtc_selfcontained … --mode=with-stl   # exit 0
```

## 6. Kthvalue A/B (H05) and BatchNorm A/B (H06)

```bash
$WS/scripts/h05_kthvalue_ab.sh    # same harness both legs; 3/3 cases; byte dumps
$WS/scripts/h06_batchnorm_ab.sh   # 6/6 checks; predeclared tolerances
# binding discipline: LD_PRELOAD=<leg>/lib/libMIOpen.so.1 + wheel-first
# LD_LIBRARY_PATH + fresh MIOPEN_CUSTOM_CACHE_DIR per leg; dladdr provenance
# is printed in-stream by both harnesses.
```

## 7. Coverage (H07) and optional YOLO (H08)

```bash
python3 $WS/scripts/h07_rtc_canaries.py     # E1-E4 arms
# BF16 probe: build per scripts/bf16_kthvalue_probe.cpp header, run under the
# same wrapper discipline on both legs (logs/h07_bf16_leg{A,B}.log)
SP=/home/amd/Desktop/YOLO_AMD/.venv/lib/python3.13/site-packages
FRESH=$WS/tmp/fresh_cache/h08_yolo
LD_PRELOAD=$WS/installs/legB/lib/libMIOpen.so.1 \
LD_LIBRARY_PATH=$SP/_rocm_sdk_core/lib:$SP/_rocm_sdk_libraries/lib:$SP/_rocm_sdk_devel/lib:/home/amd/Desktop/YOLO_AMD/.deps/miopen/lib \
MIOPEN_CUSTOM_CACHE_DIR=$FRESH XDG_CACHE_HOME=$FRESH/xdg \
/home/amd/Desktop/YOLO_AMD/.venv/bin/python $WS/scripts/h08_yolo_smoke.py
```

## Expected outcomes

| Step | Expected |
|---|---|
| patch hashes | 816946b4… / 46044d8c… / df7c3c3a…; series 48308f6d… |
| both reconstruction methods | tree b983cadd… |
| CTest | Skipped rc 0; ordinary/with-stl exit 0; positive mode exit 4 |
| kthvalue | legA/legB exit 0; 15 dump files byte-identical |
| batchnorm | 6/6 PASS both legs, identical errors |
| BF16 kthvalue | PASS both legs (k=10, [100x300], dim≥300 required by solver) |
| YOLO | TRAIN_COMPLETE / VAL_COMPLETE, legB binding asserted |
