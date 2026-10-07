# Linux Baseline Conclusion — Gate L19

Date: 2026-10-07 (revised same day after adversarial subagent review)
Branch: rca/linux-gfx1151-phase3-regression
Scope: pre-patch Linux controls only (no patch consumed yet).

> Revision note: the first version of this document claimed "fresh MIOpen
> cache created today" and used the post-BN `/proc/self/maps` presence of
> libhiprtc as RTC-path evidence. The adversarial reviewer correctly refuted
> both (ukdb birth timestamp = 2026-08-23; hiprtc is DT_NEEDED of libMIOpen).
> Both claims are replaced below by direct fresh-cache compile evidence.

## Machine

- OS: Ubuntu 24.04.4 LTS, kernel 6.17.0-1032-oem
- CPU: AMD RYZEN AI MAX+ PRO 395 (32 threads)
- GPU: AMD Radeon 8060S Graphics — gfx1151 (rocminfo `Name: gfx1151`, torch `gcnArchName='gfx1151'`), 20 CUs, 102400 MiB visible unified memory
- User in render+video groups; /dev/kfd and /dev/dri/renderD128 read-write

## Controlled software line (all inside ~/Desktop/YOLO_AMD/.venv via uv)

- uv 0.12.3, Python 3.13.15
- rocm 7.14.0 (rocm-sdk-core/devel/libraries/device-gfx1151 7.14.0, TheRock wheel layout)
- torch 2.12.0+rocm7.14.0 (hip 7.14.60850), torchvision 0.27.0+rocm7.14.0, torchaudio 2.11.0+rocm7.14.0
- ultralytics 8.4.174 (verified unmodified against wheel RECORD hashes by the adversarial reviewer)
- uv pip check: all 51 packages compatible

## System ROCm coexistence (corrected)

A system ROCm 7.2.1 EXISTS at /opt/rocm (ldconfig lists its libMIOpen.so.1,
libhiprtc.so.7, libamdhip64.so.7). The earlier claim "system ROCm not detected
on library path" was wrong. Why it does NOT contaminate this validation:

1. `/proc/self/maps` during the workload maps only venv-wheel libraries
   (runtime_unpatched/loaded_modules.txt).
2. wheel libMIOpen.so.1 RPATH resolves all DT_NEEDED into the venv
   (`$ORIGIN/../../_rocm_sdk_core/lib`, `$ORIGIN/../../_rocm_sdk_libraries/lib`).
3. MIOpen cache tags written today are the wheel build's `3.5.2.cd957402`, not
   a 7.2.1-era tag.
The contamination RISK is real and stays documented; source-build gates
(L26+) construct CMAKE_PREFIX_PATH exclusively from wheel paths.

## Required answers

| Question | Answer | Evidence |
|---|---|---|
| Kernel supported? (Ubuntu 24.04, ≥6.14 OEM required) | YES — 6.17.0-1032-oem | environment/bootstrap.txt |
| ROCm 7.14 installed? | YES — wheel stack; system 7.2.1 coexists but is not loaded (see above) | environment/uv_freeze.txt, rocm_wheel_layout.json |
| gfx1151 confirmed? | YES — rocminfo + torch device properties | environment/rocminfo.txt, torch_env.txt |
| PyTorch GPU compute works? | YES — 4096³ GEMM PASS, labeled output | baseline/gemm.txt (generator: scripts/phase3/linux/gemm_control.py) |
| Standalone HIPRTC std headers work? | YES — 6/6 compile PASS with std-facility-exercising bodies + GPU execution control PASS (libhiprtc 9.0, gfx1151) | hiprtc/baseline_header_matrix.json (generator: hiprtc_probe_linux.py) |
| BatchNorm works? | YES — 8/8 cases PASS incl. backward, on a FRESH isolated cache | baseline/batchnorm/bn_matrix_fresh_cache.txt (generator: batchnorm_matrix.py) |
| YOLO inference works? | YES — bus.jpg: 4 persons, 1 bus, `yolo_predict_exit=0` | baseline/yolo_predict.txt |
| YOLO training works? | YES — coco8 1 epoch + validation, best.pt/last.pt, `yolo_train_exit=0` | baseline/yolo_train.txt |

## Which MIOpen is loaded (proof, not inference)

`/proc/self/maps` after a spatial BatchNorm (runtime_unpatched/loaded_modules.txt):

- libMIOpen.so.1 → .venv/.../_rocm_sdk_libraries/lib/libMIOpen.so.1 (wheel build, MIOpen 3.5.2, cache tag cd957402; sha256 f5be2328…, 477251657 bytes)
- libhiprtc.so.7, libamdhip64.so.7, libamd_comgr.so.3 → _rocm_sdk_core/lib

Note (from review): hiprtc/comgr appearing mapped alongside libMIOpen is
guaranteed by DT_NEEDED and does NOT by itself prove an RTC compile occurred;
the proof of runtime compilation is below.

## Proof that spatial-BN runtime compilation actually happens (fresh cache)

`baseline/batchnorm/bn_fresh_compile_proof.txt`: running the exact 5-line BN2d
train repro with `MIOPEN_CUSTOM_CACHE_DIR` + isolated `XDG_CACHE_HOME` on an
empty directory, with `MIOPEN_ENABLE_LOGGING=1 MIOPEN_LOG_LEVEL=6`:

1. `Prefetch File is unreadable: ~/.config/miopen/batchnorm_gfx1151_20.HIP.3_5_2_cd957402.udb.txt` (per-kernel db absent)
2. `GetInvoker … algorithm miopenBatchNormForwardTrainingSpatial`
3. `Preparing kernel: MIOpenBatchNormFwdTrainSpatial` → `LoadBinary … "MIOpenBatchNormFwdTrainSpatial.cpp.o"; args … -mcpu=gfx1151` (the exact kernel that fails to compile on Windows)
4. cache-miss `SELECT … FROM kern_db` then **`INSERT OR REPLACE INTO kern_db(… kernel_blob …)`** — the compiled kernel was stored into the empty cache
5. new files after run: `3.5.2.cd957402/gfx1151_20.ukdb` (16384 B) + 5 `comgr/llvmcache-*` entries

A second BN call in the same process then hits the populated cache. This is
direct evidence that Linux batchnorm goes through fresh HIPRTC compilation of
MIOpenBatchNormFwdTrainSpatial — not a stale-cache artifact.

## Why Linux finds STL (Gate L16)

See docs/phase3/linux/LINUX_STL_BASELINE.md. Direct `-H` include trace inside
HIPRTC (raw file: hiprtc/which_stl_hiprtc_trace.txt; JSON copy:
which_stl_raw_polluted.json — the trace escapes to the process stderr, so the
program-log copy in which_stl.json is empty; both are retained):
`<type_traits>` resolves to system GCC 13 libstdc++
(/usr/include/c++/13), auto-detected by AMD clang's GCC-install detection.
Windows has no equivalent provider — the Phase-2 RCA root cause.

## Deviations / notes (transparency)

1. **Network flakiness**: github.com/ultralytics.com downloads intermittently
   fail/retry. bus.jpg retried once then succeeded; coco8.zip failed 3x then
   succeeded on a later attempt during the first train run ("Dataset download
   success (189.5s)" in the first-run log — the dataset was NOT pre-existing;
   corrected from earlier draft). Model/artifact downloads are cached outside
   the repo.
2. **Ultralytics AMP check reported anomalies and auto-disabled AMP** for the
   baseline train runs. Manual fp16 controls (conv fp16 finite/close-to-fp32,
   half GEMM finite, autocast BN fp32) all pass, so this is most plausibly
   the AMP-check asset download failing over the flaky network, not a GPU
   fp16 defect. Training itself completed cleanly both times. For patched-run
   symmetry (Gate L39) both amp=default and amp=False will be run.
3. **Ultralytics settings.json** (machine-global, pre-existing) redirects
   runs/ to ~/Desktop/OpenVINO-Notebooks-on-AMD/runs and datasets_dir to
   ~/Desktop/datasets. Runs stay outside the RCA repo; recorded deliberately.
   The machine also has prior AMD ML history: MIOpen cache dirs from Aug/Sep
   (incl. 3.5.2.cd957402 born 2026-08-23) and empty ultralytics run dirs from
   earlier today — none touch the venv-controlled stack identity.
4. **No passwordless sudo**: build tools that needed installing came from uv
   (ninja 1.13.2) or the ROCm wheel (AMD clang 23.0.0). System already had
   cmake 3.28.3, gcc/g++ 13.3.0, pkg-config, build-essential.

## Baseline verdict

```text
LINUX UNPATCHED BASELINE: PASS
```

The exact Windows-failing 5-line BatchNorm2d repro passes on Linux (with
direct fresh-cache HIPRTC-compile proof), all spatial-BN variants pass, the
standalone HIPRTC header matrix passes 6/6 (std-exercising bodies) with a
passing GPU execution control, and YOLO inference + training complete with
recorded exit 0 on the Radeon 8060S. This satisfies the Linux leg's
precondition: "Linux PASS → patched Linux PASS" can be tested once the
Phase-3 patch handoff exists.
