# Validation Matrix — PR #13437 final HEAD `f0f330c4` (Windows, 2026-10-15)

All legs executed this round against a clean build of the pinned final HEAD
(unless stated otherwise). GPU: Radeon 8060S / gfx1151; OS: Windows 11
10.0.26200; ROCm wheel stack 7.14.0; PyTorch 2.12.0+rocm7.14.0.

| Test | Source SHA | Result | Raw log | Binary provenance |
|---|---|---|---|---|
| B — HIPRTC no-STL regression gtest (`CPU_HipRtcSelfContained_NONE.RtCompilesInlineKernelWithoutHostStl`) | `f0f330c4` (build tree) | **PASS** (1/1; 5 fresh nonce'd RTC compiles; kernel launched, values verified; with-STL control also ran) | `raw/hiprtc/B_final_gtest_run.log` | cache label `3.6.2.f0f330c4`; `GetLibPath C:\bfin\bin`; exe SHA `5f0c3f13…` |
| C — Negative control (unpatched baseline + final test file) | `b8cf0e7b` + test blob from `f0f330c4` | **EXPECTED_FAIL** — fails with exactly `miopen_type_traits.hpp:151:10: fatal error: 'type_traits' file not found`; ambient-STL leg still passes | `raw/negative_control/C_pristine_gtest_run_f0f330c4test.log` | cache label `3.6.2.b8cf0e7b`; assertion at final-file line 147 |
| D — BatchNorm fwd/bwd vs CPU reference (wheel-swap) | `f0f330c4` (DLL in wheel) | **PASS** — all finite; max errs 9.5e-07 (y) … 3.3e-06 (running_var); two runs (v2 timestamped) | `raw/batchnorm/D_batchnorm_patched_v2.log` (run1 kept as `_run1.log`) + `swap_transcript_v2.log` | in-process module path = wheel path; swap transcript hashes: `74b4ee03…` → `c739cb0e…` → restored `74b4ee03…` |
| E — kthvalue gtest (radix.hpp consumer) | `f0f330c4` (build tree) | **PASS** 27/27 (FP32/FP16/BFP16 × 9) | `raw/kthvalue/E_kthvalue_patched.log` + `_l6_isolated.log` | exe SHA `aecb6ce4…`; isolated-DB l6 log: cache label `3.6.2.f0f330c4`, `C:\bfin\bin`, **3 fresh dtype compiles + 27 launches** |
| F — YOLO26n COCO8 1-epoch smoke train (wheel-swap) | `f0f330c4` (DLL in wheel) | **PASS** — epoch completed, val metrics normal, AMP checks passed, no missing-STL/new MIOpen failure | `raw/yolo/F_yolo26n_coco8.log` (hostname redacted, disclosed) | in-process module path = wheel path; DLL SHA `c739cb0e…` during run; wheel restored `74b4ee03…` |

## Not executed this round (explicit)

| Item | Status | Note |
|---|---|---|
| Linux local revalidation of `f0f330c4` | NOT_RUN | No Linux runner in this round. Upstream CI covers Linux; the test's comgr-injects-STL environment reports GTEST_SKIP by design (tri-state behavior documented in the test source). |
| Upstream CI (approval-gated workflows) | BLOCKED | Pending maintainer approval on the PR; no new approval requests were triggered by this evidence round. |

## Cross-round integrity

The earlier (pre-squash, 2026-10-14/15) validation of the working tree that
became `f0f330c4` reported the same outcomes (B PASS, C exact-signature
fail, D identical seeded numerics, E 27/27, F 1-epoch PASS with AMP
offline-skipped). That round's logs embed cache label `3.6.2.e4b9174a-dirty`
and a 198-line pre-final test file, so they are retained locally as
supporting context only and are **not** counted as final-HEAD evidence.
