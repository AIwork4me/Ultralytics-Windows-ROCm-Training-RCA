# FUNCTIONAL REGRESSION MATRIX — Round-3 (d4b574ac), 2026-10-16

Machine: Windows 11, Ryzen AI MAX+ 395 / Radeon 8060S (gfx1151), ROCm 7.14.0 wheels,
torch 2.12.0+rocm7.14.0 (env `yolo_amd`), HIPRTC v.9.0 (wheel), AMD Clang 23.0.0git (ROCm llvm-project 46fcb339fb61119b337f973c7ca9e710a319fdd0, patched build)
(toolchain details in build/toolchain.txt). Round-2 column = prior validated evidence on
f0f330c4 (Phase 5.7); Round-3 column = fresh runs this mission — no copied results.

## Matrix

| Test | Round-2 (f0f330c4) | Round-3 (d4b574ac) — this run | Required | Verdict |
|---|---|---|---|---|
| HIPRTC no-STL gtest (`CPU_HipRtcSelfContained_NONE.RtCompilesInlineKernelWithoutHostStl`) | PASS | `raw/hiprtc/B_r3_gtest_run.log`: **PASSED**, 1 test; fresh cache home `C:\r3home_b` (redirected USERPROFILE); **runtime cache label `3.6.2.d4b574ac`** (revision label corroborated by build and binary records; label alone is not a clean-tree attestation); 5 fresh nonce-keyed RTC compiles through the production path (3 isolated with `-nostdinc`, 2 ambient controls); kernel launched on gfx1151; out values verified by the test's internal asserts (3/5/9/11 pattern); no GTEST_SKIP | PASS | **PASS** |
| Host-STL compilation control | PASS | RelWithDebInfo build of MIOpen + gtests from C:\w58 @ d4b574ac succeeded (`build rc=0`, `build/build_b58.log`; the final progress counter is 781/782). The positive HIPRTC log separately records successful ambient STL-use and selfcontained compile controls. This establishes host-library/test build and ambient-STL coverage; embedded RTC kernel strings are not proof that every GPU kernel TU compiled offline | PASS | **PASS** |
| Missing-STL negative control | EXPECTED_FAIL `type_traits file not found` | `raw/negative_control/C_r3_pristine_run.log`: pristine b8cf0e7b binary (C:\bwp), exit 1, `miopen_type_traits.hpp:151:10: fatal error: 'type_traits' file not found` — exact original signature; regression test still detects the defect after #error-guard removal | EXPECTED_FAIL | **EXPECTED_FAIL ✓** |
| BatchNorm training fwd (y, running stats) | PASS (y err 9.537e-07) | `raw/batchnorm/D_r3.log`: finite=True; y 9.537e-07; running_mean 6.985e-10; running_var 3.338e-06 vs CPU ref | PASS | **PASS** |
| BatchNorm training bwd (grads x/w/b) | PASS | same run: grad x 1.174e-12, w 5.588e-09, b 6.580e-10; all finite | PASS | **PASS** |
| Round-2 vs Round-3 printed error-summary A/B | n/a | `raw/batchnorm/D_r2_ab.log` (bfin DLL) vs D_r3 (b58 DLL): **all six printed max-error summaries identical** under identical seeds/shapes/dtype; saved tensors were not retained, so tensorwise identity is not established | error-summary comparison | **PRINTED SUMMARIES MATCH** |
| kthvalue gtest | 27/27 | `raw/kthvalue/E_r3_kthvalue_warm.log` (first execution in fresh cache home → cold cache): **27/27 PASSED** (FP32/FP16/BF16 × 9 cases); 3 fresh runtime compiles (exactly 3 `MIOpenKthvalue.cpp.obj` blobs verified inside the fresh home's ukdb; sibling `E_r3_kthvalue_cold.log` is a dead `/usr/bin/time` artifact — the timed cold leg never ran) | 27/27 | **PASS** |
| YOLO26n COCO8 1-epoch | PASS | `raw/yolo/F_r3.log`: GPU train completed (1 epoch, 0.024 h, 12.3 ms/img inference), losses finite, validation ran (mAP50 0.943), no missing-STL failure | PASS | **PASS** (AMP disclosure below) |
| Linux | CI green on f0f330c4 | NOT run locally (no Linux GPU); classification in PHASE6_CROSS_PLATFORM.md; CI re-run triggers on push | disclose | **DISCLOSED** |

## AMP check — explicit classification (mission §9.5)

Phase 5.7 reported AMP checks PASSED (f0f330c4 DLL, 2026-10-15). This round the AMP check
RAN (downloaded its model) and reported anomalies → Ultralytics disabled AMP for training;
training itself completed in FP32. Control experiment (this round, same machine state):

| DLL under test | check_amp verdict |
|---|---|
| Round-3 build d4b574ac | FAIL (`raw/yolo/AMP_B1.log`) |
| Round-2 build f0f330c4 | FAIL (`raw/yolo/AMP_A1.log`) |
| **Pristine shipping wheel 74b4ee03** | FAIL (`raw/yolo/AMP_WHEEL.log`) |

The anomaly also reproduces on the untouched shipping wheel and Round-2 library. This argues
against a Round-3-specific cause; it does not establish the root cause or validate AMP training. The F training run is
classified PASS (fp32) with this difference from 5.7's environment state explicitly recorded.

### Running-stat reference limitation

The executed `scripts/d_batchnorm.py` uses `var(..., unbiased=False)` for the running-variance
reference, whereas the running-stat convention uses an unbiased estimate. The printed
3.338e-06 residual is a finiteness/tolerance observation, not an exact estimator-matched
reference check. Forward output and backward gradients are separately compared against
CPU BatchNorm. The original executed script and logs are preserved.

## Binary provenance

- Round-3 build: `C:\b58` from clean worktree `C:\w58` @ d4b574ac —
  MIOpen.dll SHA256 `42d261caec77bf3149b336d55b12dd388e988da97a84cf79688a6f4af19b23cc`,
  test_hiprtc_selfcontained.exe `b1f130a0…`, test_kthvalue.exe `47e0fa30…`
  (`provenance/binary_sha256_b58.txt`). Runtime label proof: `3.6.2.d4b574ac` in B log
  (no `-dirty`); negative-control binary separately labeled `3.6.2.b8cf0e7b`.
- Functional D/F/AMP transcripts record hash-verified restoration of shipping wheel
  `74b4ee038803…`. Abandoned `raw/perf/perf_bn_*.log.swap_transcript` files instead
  expose busy-file swap/restore failures, leaving A's `c739cb0e…` DLL; their B-labelled
  timings are invalid. The later A transcript records successful restoration at 15:34:50.
  Final `perf2_*` timings use per-process preload and are distinct from those failed legs.
- In-process module-path proof printed by every python-based test (`MIOpen.dll loaded from: …\wheel bin`).

**Gate B+C: PASS** — no functional regression; negative control preserved; equivalence vs
Round-2 identical printed error summaries for the measured BatchNorm A/B quantities, with the reference limitation above.
