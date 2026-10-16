# PERFORMANCE A/B REPORT — Round-2 (f0f330c4) vs Round-3 (d4b574ac)

Same physical GPU (Radeon 8060S, gfx1151), driver, ROCm 7.14.0 wheels, torch
2.12.0+rocm7.14.0, HIPRTC v9.0 (identical wheel compiler both sides), RelWithDebInfo builds
of both variants, identical kernel parameters/shapes/dtypes, same intended machine-state protocol (see the drift and contamination limitations below).
The unpatched b8cf0e7b tree is NOT a performance baseline (it cannot run the affected path).

## 1. Generated-code equivalence (strongest evidence)

The original run associated kernel artifacts with cache labels `3.6.2.f0f330c4` (A) and
`3.6.2.d4b574ac` (B). Archived caches retain three kthvalue variants per label; those
bz2 blobs can be re-extracted and matched to the retained ELF files. Seven BatchNorm
variants are preserved as standalone paired ELF/disassembly files, but their originating
cache rows/options were not archived. Their instruction identity is independently
reproducible from these artifacts; their source/build association relies on the original
A/B naming and run narrative, not independent cache-to-build attestation. `.text` comparisons:

| Kernel | Variants | Result |
|---|---|---|
| MIOpenKthvalue.cpp (radix path; consumes changed headers) | FP32, FP16, BF16 | **ISA instruction-identical** (1023/1044/1020 instr, 0 diff) |
| MIOpenBatchNormBwdSpatial.cpp | 3 retained variants | **ISA instruction-identical** (1289/663/974 instr, 0 diff) |
| MIOpenBatchNormFwdTrainSpatial.cpp | 4 retained variants | **ISA instruction-identical** (453/941/820/747 instr, 0 diff) |

Whole-code-object hashes differ, while `.text` and `.note` are equal. Differing
non-instruction sections include `.dynstr`, `.gnu.hash`, `.hash`, `.dynamic`, `.strtab`
and `.symtab`, depending on the pair; the validator enumerates these differences.
GPU instructions are identical between the ten retained A/B artifact pairs — **10/10 identical**. Closure auditor C
independently compares ELF `.text` bytes and retained instruction dumps; only kthvalue
can also be re-extracted from the committed cache snapshots. This supports unchanged device instruction streams for these variants. It does not exclude
compile-time, host-side, launch, cache, scheduling or untested-path effects; timing causality
cannot be decided from ISA identity alone.

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
**INCONCLUSIVE timing evidence** — recorded differences are small and both-signed;
ISA identity (§1) is a separate scoped observation, not timing validation.

## 4. Warm BatchNorm fwd/bwd (CUDA events, 30 warmup + 200 iters, ABBA legs, per-leg DLL preload with in-process handle proof)

| Workload | A median (ms) | B median (ms) | Δ | Verdict |
|---|---|---|---|---|
| fwd 20×100×35×45 | 0.248 | 0.292 | +17.6% | INCONCLUSIVE (sub-ms, host/desktop-shared iGPU; bwd of same shape is −11.4% — mixed directions do not establish a causal regression) |
| bwd 20×100×35×45 | 0.604 | 0.535 | −11.4% | INCONCLUSIVE (same) |
| fwd 32×256×56×56 | 2.945 | 2.911 | −1.1% | INCONCLUSIVE timing quality; no confirmed material regression in reported medians |
| bwd 32×256×56×56 | 6.297 | 6.051 | −3.9% | INCONCLUSIVE timing quality; negative event minimum in B3 |
| fwd 64×512×28×28 | 3.809 | 3.682 | −3.3% | INCONCLUSIVE timing quality; no confirmed material regression in reported medians |
| bwd 64×512×28×28 | 5.520 | 5.560 | +0.7% | INCONCLUSIVE timing quality; no confirmed material regression in reported medians |

Within-config leg-pair spreads reach ~15–17% on individual metrics (e.g. A fwd 32×256
3.169 vs 2.720; B bwd 20×100 0.581 vs 0.488); GPU-bound shape medians are all within ±5%
with mixed sign (B mostly faster). No confirmed material regression appears in reported GPU-bound medians; timer anomalies
and unavailable individual samples prevent a confident timing PASS. The sub-ms shape is
noise-bound (INCONCLUSIVE; no repeatable material regression established by this sample).
ISA identity in §1 narrows device-code risk but is not a whole-program performance proof.

## 5. Kernel selection / solver / launch observations

- The committed cache snapshots contain three common kthvalue name/option pairs per
  label, with duplicate `cache/` and `.miopen/cache/` copies. They do not retain the
  historical 28-entry cache or BatchNorm rows. No broad kernel-count/solver-selection
  conclusion is independently supported by these snapshots. The five-compile HIPRTC
  test count is separately established by its logs. Seven BN ELF pairs remain inspectable.
- Code-object sizes: identical lengths for every compared kernel (12944/7952/10000/6688/…
  bytes = A=B).

## 6. YOLO26n secondary metric

R3 run: 1 epoch = 0.024 h (86 s) on COCO8 batch 8 — consistent with the R2-era evidence
runs (5.7 F log); not re-run under A this round (AMP-check environment anomaly documented
in FUNCTIONAL_REGRESSION_MATRIX.md). **NOT_RUN as a paired A/B** (secondary metric only).

## 7. Noise/confidence limitations (disclosed)

- iGPU shares memory/power with the OS desktop; within-config spreads up to 20% on
  compile-dominated runs and approximately 15–17% on some warm leg-pair metrics.
- Two benchmark contamination incidents were addressed before the final
  reported run: (1) an orphaned benchmark process from an aborted run kept computing on the GPU
  (invalidating one intermediate ABBA attempt; it was terminated via WMI and the wheel DLL
  it had locked was restored to pristine `74b4ee03…`, verified); (2) a first preload attempt
  failed on DLL-dependency resolution (fixed with explicit `add_dll_directory` set). The
  final reported data (`raw/perf/perf2_*.log`) used the intended cleanup protocol and
  per-leg in-process module-handle proof. This does not prove absence of all background
  work. Negative event minima are retained in final legs: A1 sub-ms forward −0.29501 ms,
  A4 sub-ms forward −0.05075 ms, B2 sub-ms forward −0.40767 ms, and B3 GPU-bound
  backward 32×256×56×56 −3.21978 ms. Individual 200-sample arrays were not archived,
  so their impact on reported medians cannot be independently bounded. Warm timing
  evidence is INCONCLUSIVE; medians remain observational data, not validated timing PASS.
- Cold gtest pairing was order-sensitive (upward thermal/drift trend); retained as
  INCONCLUSIVE rather than claimed as PASS.
- The YOLO run log itself records an on-machine timing anomaly
  (`MIOpen: Error [EvaluateInvokers] … Invalid elapsed time detected … elapsed <= 0`),
  consistent with the desktop-shared-iGPU noise environment described above (reviewer C
  observation; the smoke run completed, but the cause of the timing error is unproven).

## Summary verdicts

| Workload | Verdict |
|---|---|
| Generated code (kthvalue ×3, BN train ×7) | **PASS** (ISA identical) |
| Cold HIPRTC compile time | **INCONCLUSIVE** (within machine drift; no reproducible regression) |
| Warm kthvalue | **INCONCLUSIVE timing evidence** |
| Warm BatchNorm (GPU-bound shapes) | **INCONCLUSIVE timing quality; no confirmed material regression in reported medians** |
| Warm BatchNorm (sub-ms shape) | **INCONCLUSIVE** (noise-bound, both-signed) |
| YOLO26n paired A/B | **NOT_RUN** (single-leg secondary metric only) |

**Scoped conclusion:** ten matched variants have identical instruction streams, and the
measured warm GPU-bound BatchNorm cases show no confirmed material regression. Cold
compilation and sub-millisecond metrics remain INCONCLUSIVE. No complete YOLO paired A/B
exists. These observations do not establish universal performance non-regression.
