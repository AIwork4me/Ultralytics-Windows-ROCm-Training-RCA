# KTHVALUE RUNTIME A/B — Direct MIOpen API (gfx1100)

## Execution path (log-proven)

`miopenKthvalueForward → KthvalueFwd solver → MIOpenKthvalue.cpp (RTC) → radix.hpp`

Both legs' MIOPEN_LOG_LEVEL=6 logs contain, per case: `FindSolutionImpl] KthvalueFwd
(not searchable)`, kern_db SELECT miss for `MIOpenKthvalue.cpp.o` with
`-mcpu=gfx1100`, `HIPRTC v.9.0`, `SaveBinary`/`INSERT OR REPLACE` (2 rows per leg:
float+half), and `[run] kernel_name = KthvalueFwd` with grid dims. The per-leg SQLite
ukdbs were independently queried by the Gate-L08 reviewer.

## Cases (deterministic, tie-free; established Phase-3/5.2 harness)

| Case | Shape | dtype | k | dim | keepDim | Leg A | Leg B |
|---|---|---|---|---|---|---|---|
| FP32-2D-nokeep | [100,500] | FP32 | 10 | -1 | no | PASS | PASS |
| FP32-3D-keep-explicit-dim | [10,20,300] | FP32 | 137 | 2 | yes | PASS | PASS |
| FP16-4D-keep-kmax | [8,3,10,2000] | FP16 | 2000 | -1 | yes | PASS | PASS |

## Numerical results (identical on both legs)

- value_mismatches=0, index_mismatches=0, max_abs_err=0 vs CPU reference, every case.
- 15/15 dump files byte-identical between legs (input, output, indices, CPU-expected
  values and indices) — `cmp`-verified and independently re-verified by the L08 reviewer
  (including decoding output.bin vs expected_values.txt).
- Exact-match expectation is sound: kthvalue is a selection operator over pairwise-distinct
  values exactly representable in FP32/FP16 (0.25-multiples); no arithmetic rounding.

## Harness and caches

- Same binary both legs: `kthvalue_runtime_harness_gfx1100`, sha256
  `b830b37a5aa7aef37da8c79e3ceb30435fd631b99dda29516f2ed36c152e7ef8`
  (mission brief carries a 65-char typo of this value; see L00 erratum).
- Fresh per-leg per-label caches (516 files created during each run; wrapper refuses
  non-empty dirs).
- In-stream dladdr PROVENANCE per leg; wrapper LD_PRELOAD verified.

## Scope boundaries (Reviewer A, Gate L12)

Radix int32/int64 encode branches and BF16 kthvalue were compiled on both legs but not
exercised at runtime by these cases; no-regression claim is scoped to FP32/FP16 cases run.
