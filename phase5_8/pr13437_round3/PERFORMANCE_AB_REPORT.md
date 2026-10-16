# PERFORMANCE A/B REPORT — Round-2 (f0f330c4) vs Round-3 (d4b574ac)

Same physical GPU (Radeon 8060S, gfx1151), driver, ROCm 7.14.0 wheels, torch
2.12.0+rocm7.14.0, HIPRTC v9.0 (identical wheel compiler both sides), RelWithDebInfo builds
of both variants, identical kernel parameters/shapes/dtypes, same machine state protocols.
The unpatched b8cf0e7b tree is NOT a performance baseline (it cannot run the affected path).

## 1. Generated-code equivalence (strongest evidence)

Runtime-compiled kernel code objects were extracted from the per-label MIOpen kernel caches
(`3.6.2.f0f330c4` vs `3.6.2.d4b574ac`), bz2-decompressed, and their `.text` sections
disassembled (wheel llvm-objdump):

| Kernel | Variants | Result |
|---|---|---|
| MIOpenKthvalue.cpp (radix path; consumes changed headers) | FP32, FP16, BF16 | **ISA instruction-identical** (1023/1044/1020 instr, 0 diff) |
| MIOpenBatchNormBwdSpatial.cpp | 3 option-sets | **ISA instruction-identical** (1289/663/974 instr, 0 diff) |
| MIOpenBatchNormFwdTrainSpatial.cpp | 4 option-sets | **ISA instruction-identical** (453/941/820/747 instr, 0 diff) |

Whole-code-object hashes differ only in metadata: `.note` is byte-identical; every differing
byte sits in the `__hip_cuid_<id>` compile-unit string in `.dynstr` and the dependent
`.gnu.hash`/`.hash`/`.relro_padding`/`.dynamic` tables (source text changed ⇒ compile-unit
name hash changed). The GPU machine code Round-3 ships is the
same as Round-2 for every comparable kernel — **10/10 identical** (independently re-extracted
and re-compared byte-by-byte by reviewer C). Performance differences
below therefore cannot originate from the patch; they measure machine noise.

## 2. Cold HIPRTC compilation

`test_hiprtc_selfcontained` (5 nonce'd RTC compiles) internal gtest duration, interleaved
run order A,B,B,A,A,B (fresh kernel-cache home each run):

- A: 18084, 18286, 21702 ms (median 18286; within-config spread **20%**)
- B: 19845, 20340, 21992 ms (median 20340; +11% median, +1.3% on the time-matched last pair)

Round-3's headers are strictly shorter (−61 lines), the RTC compiler binary and kernel
source are identical, and the last pair (both slow, machine warmed) shows +1.3%; the
early-pair +10% coincides with an upward time trend across the whole session (A itself
drifts 18.1→21.7 s). **INCONCLUSIVE — no reproducible compile-time regression demonstrated;
observed deltas are within demonstrated machine drift.** Compile counts: 5 vs 5 identical.

## 3. Warm kthvalue (gtest wall/case time, fresh vs warm cache)

- Cold suite (fresh cache, includes 3 RTC compiles): A 18.5/19.8 s vs B 20.4/19.6 s (mixed)
- Warm suite: A 15.2/15.5 s vs B 15.1/14.5 s (B slightly faster)
- Per-case sums: cold A 19448 ms vs B 19355 ms; warm A 15264 ms vs B 14222 ms
**PASS** — differences small and both-signed; ISA identical by construction (§1).

## 4. Warm BatchNorm fwd/bwd (CUDA events, 30 warmup + 200 iters, ABBA legs, per-leg DLL preload with in-process handle proof)

| Workload | A median (ms) | B median (ms) | Δ | Verdict |
|---|---|---|---|---|
| fwd 20×100×35×45 | 0.248 | 0.292 | +17.6% | INCONCLUSIVE (sub-ms, host/desktop-shared iGPU; bwd of same shape is −11.4% — opposite signs = noise) |
| bwd 20×100×35×45 | 0.604 | 0.535 | −11.4% | INCONCLUSIVE (same) |
| fwd 32×256×56×56 | 2.945 | 2.911 | −1.1% | PASS |
| bwd 32×256×56×56 | 6.297 | 6.051 | −3.9% | PASS |
| fwd 64×512×28×28 | 3.809 | 3.682 | −3.3% | PASS |
| bwd 64×512×28×28 | 5.520 | 5.560 | +0.7% | PASS |

Within-config leg-pair spreads reach ~15–17% on individual metrics (e.g. A fwd 32×256
3.169 vs 2.720; B bwd 20×100 0.581 vs 0.488); GPU-bound shape medians are all within ±5%
with mixed sign (B mostly faster). **PASS** for GPU-bound workloads; sub-ms shape is
noise-bound (INCONCLUSIVE, no reproducible regression — and §1 makes a code cause
impossible for the RTC-compiled BN kernels: identical machine code).

## 5. Kernel selection / solver / launch observations

- Identical kernel names + option sets in both cache labels (28 common entries; label dirs
  differ only by run history). No extra HIPRTC compilations (same compile counts), no
  generated-kernel-count change, no solver-selection change (same Find-mode defaults).
- Code-object sizes: identical lengths for every compared kernel (12944/7952/10000/6688/…
  bytes = A=B).

## 6. YOLO26n secondary metric

R3 run: 1 epoch = 0.024 h (86 s) on COCO8 batch 8 — consistent with the R2-era evidence
runs (5.7 F log); not re-run under A this round (AMP-check environment anomaly documented
in FUNCTIONAL_REGRESSION_MATRIX.md). **NOT_RUN as a paired A/B** (secondary metric only).

## 7. Noise/confidence limitations (disclosed)

- iGPU shares memory/power with the OS desktop; within-config spreads up to 20% on
  compile-dominated runs and ~5-9% on sub-ms kernels.
- Two benchmark contamination incidents occurred and were fully remediated before the final
  clean run: (1) an orphaned benchmark process from an aborted run kept computing on the GPU
  (invalidating one intermediate ABBA attempt; it was terminated via WMI and the wheel DLL
  it had locked was restored to pristine `74b4ee03…`, verified); (2) a first preload attempt
  failed on DLL-dependency resolution (fixed with explicit `add_dll_directory` set). The
  final reported data (`raw/perf/perf2_*.log`) ran with proven-clean machine state and
  per-leg in-process module-handle proof.
- Cold gtest pairing was order-sensitive (upward thermal/drift trend); retained as
  INCONCLUSIVE rather than claimed as PASS.
- The YOLO run log itself records an on-machine timing anomaly
  (`MIOpen: Error [EvaluateInvokers] … Invalid elapsed time detected … elapsed <= 0`),
  consistent with the desktop-shared-iGPU noise environment described above (reviewer C
  observation; immaterial to correctness).

## Summary verdicts

| Workload | Verdict |
|---|---|
| Generated code (kthvalue ×3, BN train ×7) | **PASS** (ISA identical) |
| Cold HIPRTC compile time | **INCONCLUSIVE** (within machine drift; no reproducible regression) |
| Warm kthvalue | **PASS** |
| Warm BatchNorm (GPU-bound shapes) | **PASS** |
| Warm BatchNorm (sub-ms shape) | **INCONCLUSIVE** (noise-bound, both-signed) |
| YOLO26n paired A/B | **NOT_RUN** (single-leg secondary metric only) |

**Gate C: PASS for claiming performance non-regression** — anchored on identical generated
machine code for all comparable kernels plus no reproducible timing regression in any
paired measurement.
