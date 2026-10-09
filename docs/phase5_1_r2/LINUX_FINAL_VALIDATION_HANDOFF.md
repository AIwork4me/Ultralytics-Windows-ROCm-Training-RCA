# LINUX W7900 FINAL VALIDATION HANDOFF — P5.1-CANDIDATE-R2

Audience: the independent Linux CodeX/validator operating the Radeon PRO
W7900 (gfx1100) machine. This document supersedes the R1 handoff
(docs/phase5_1/LINUX_FINAL_VALIDATION_HANDOFF.md) for validation purposes.
R2 identities ONLY — no R1 value in this document is a target identity.

## 0. Pin the evidence (do this first)

```
git fetch origin
git checkout <R2_EVIDENCE_COMMIT>     # printed in the R2 publication record;
                                      # branch phase5.1/windows-r2-ci-portability-freeze
                                      # verify: git rev-parse HEAD == published SHA
python scripts/phase5_1_r2/verify_patch_identity.py HEAD      # expect 25/25
python scripts/phase5_1_r2/verify_final_handoff.py HEAD       # expect 39/39
```

Authoritative manifest: `findings/phase5_1_r2/FINAL_HANDOFF.json`
(candidate `P5.1-CANDIDATE-R2`). The R1 manifest
(findings/phase5_1/FINAL_HANDOFF.json at 4949076 on the R1 branch) stays
immutable but is SUPERSEDED — do not validate against it.

## 1. Exact R2 identities (frozen)

- Upstream base: `7c5866144ac4b879be442563e2b49fa1c142ea36`
  (ROCm/rocm-libraries develop).
- Ordered R2 commits:
  1. `01a77dab8c4cf23d1e49273fa3c88bb0bb4fc887` — MIOpen: keep RTC type traits self-contained when no host STL is reachable
  2. `8188b803b8304fc5933caa52ee27a58d01a78b04` — MIOpen: make remaining RTC kernel std includes self-contained
  3. `f18c4de94b229bbe3e8501d70e3e2461425c69de` — MIOpen: add portable HIPRTC no-host-STL regression test
- R2 source tree SHA1: `b983caddf9f9f561e7d1b590deadb16267c2de15`
- Canonical patches (apply/git-am in this order; LF bytes; series
  algorithm sha256_file_concat_v1 = SHA256 of the three files'
  concatenated bytes, no separator):
  - `patches/phase5_1_r2/canonical/0001-MIOpen-keep-RTC-type-traits-self-contained-when-no-h.patch`
    SHA256 `816946b4c8f52dbe044b62ae47b65c346989337eb63557f7bd1b829a1e71a76c`
  - `patches/phase5_1_r2/canonical/0002-MIOpen-make-remaining-RTC-kernel-std-includes-self-c.patch`
    SHA256 `46044d8c9511fe3575ce8709623b18c627cc25bd076cb3cf231dc00c6ef1f460`
  - `patches/phase5_1_r2/canonical/0003-MIOpen-add-portable-HIPRTC-no-host-STL-regression-te.patch`
    SHA256 `df7c3c3a3386732931b85d682c0d58638f7b4b48e169cede1cae254642d67f7e`
  - Series SHA256: `48308f6dccfd80f099a458ad5033f815d95f86d2ab54dba1a0344c976b5a3f02`
- Acceptance after `git am` of the three patches:
  `git write-tree` == `b983caddf9f9f561e7d1b590deadb16267c2de15`.

DO NOT apply any patches/phase5_1/canonical/* (R1, superseded) or
patches/phase3, phase5 (older lineages).

## 2. Environment (W7900 leg)

- GPU: Radeon PRO W7900, target gfx1100. OS: Ubuntu 24.04.4.
- ROCm 7.14.1 isolated wheel SDK; PyTorch 2.12.0+rocm7.14.1.
- Preserve clean ROCm 7.14.1 library isolation — no system ROCm 7.2.1
  contamination (`ldd`/`LD_LIBRARY_PATH` audit; the Phase-5.2 env wrappers
  `env_rocm7141.sh` remain the reference method).
- All caches fresh: MIOPEN_USER_DB_PATH/MIOPEN_USER_CACHE_PATH and
  AMD_COMGR_CACHE pointed at empty temp dirs for every Kthvalue/BatchNorm
  run (fresh-cache requirement — proves RTC compile actually happens).

## 3. Legs to build

- LEG A — FROZEN BASE: source at `7c586614` (no patches), built with the
  established leg wrapper (BUILD_TESTING=OFF leg build; identity recorded).
- LEG B — R2 SOURCE: `git am` the three R2 patches onto `7c586614`;
  verify tree SHA `b983cadd…` BEFORE building; same flags as Leg A
  (single-variable A/B discipline), GPU_TARGETS=gfx1100.

## 4. Required tests (all raw logs + exit codes into evidence/)

1. CTest portability (NEW in R2 — a separate clean test build with
   `-DBUILD_TESTING=ON`, MIOPEN_USE_HIPRTC=ON):
   - Build target `test_hiprtc_selfcontained` WITHOUT external manual
     include/link workarounds (the R2 CMake now links the imported
     `hiprtc::hiprtc` target when the package exports it — F-C2-2 fixed).
   - `ctest -N -R '^test_hiprtc_selfcontained$'` discovers the test.
   - `ctest --output-on-failure -R '^test_hiprtc_selfcontained$'`:
     on Linux ROCm 7.14.1 full no-STL isolation is NOT reproducible
     (libhiprtc-builtins embeds the headers) — the test's probe returns
     INCONCLUSIVE (exit 4) and CTest MUST report **Skipped / Not Run**
     with ctest rc 0 (F-C2-1/F-C2-3 fixed). It must NOT report Failed,
     and a Skip must never be counted as a genuine kernel PASS.
   - Direct binary matrix: `--mode=ordinary` and `--mode=with-stl` must
     each independently PASS (exit 0). `--mode=negative` on the FROZEN
     BASE tree (run the Leg-B-built binary against Leg A's kernels dir)
     must FAIL with the exact missing-STL signature (exit 1).
   - Restricted-list parity spot check (optional but recommended):
     configure a third tree with `-DMIOPEN_TEST_BFLOAT16=ON` and confirm
     the test registers as `echo skipped` + DISABLED (policy parity).
2. Direct MIOpen Kthvalue A/B (both legs):
   - Run the direct `miopenKthvalueForward` harness
     (linux-w7900/phase5.2.1/wrappers/kthvalue_runtime_harness_gfx1100.cpp)
     on Leg A and Leg B; require true KthvalueFwd dispatch and HIPRTC
     compilation of MIOpenKthvalue.cpp (MIOPEN_LOG_LEVEL=6, log lines
     captured), identical deterministic outputs and indices between legs
     and vs CPU reference (exact match), fresh caches per run.
   - Cases (established): FP32 [100,500] k=10 dim=-1; FP32 [10,20,300]
     k=137 dim=2 keepDim; FP16 [8,3,10,2000] k=2000 dim=-1 keepDim.
3. BatchNorm + numerics: forward/backward correctness vs CPU fp64
   reference within the established tolerances (y<=1e-5, dx<=1e-5,
   dw<=1e-4, db<=1e-5, rm<=1e-4, rv_rel<=1e-3), fresh cache, on Leg B;
   no-STL fresh-profile workload equivalent to the Windows R28A cell
   (note: Linux host cannot reproduce no-STL — record honestly).
4. Library load provenance: `dladdr` on the MIOpen symbol in-process on
   each leg; record resolved libMIOpen.so path + SHA256; verify it is the
   leg's own build, not a wheel/system copy.
5. Optional: YOLO26n coco8 1-epoch amp=False smoke on Leg B
   (non-blocking; record exit status + weights).

## 5. Consumer update requirement (IMPORTANT)

The Linux Phase-5.2 consumer scripts may still pin R1 identities
(R1 series `797a69b5…`, R1 tree `605d0d21…`, R1 patches). For R2
validation, update those pins explicitly to the Section-1 identities.
Do NOT bypass integrity checks to force acceptance; the checks must pass
against the NEW hashes.

## 6. Reporting rules

- Windows CodeX claims NOTHING about Linux results. Linux validation
  results belong to this Linux validator's own evidence branch.
- Record: raw logs, exit codes, tree/commit SHAs per leg, binary
  SHA256s, GPU/arch confirmation, cache-freshness proof.
- If any expectation fails (e.g. CTest renders Failed instead of
  Skipped, ordinary/with-stl fail, Kthvalue mismatch), report BLOCKER
  with the raw log — do not tune the test to green.
