# Kthvalue Runtime Closure — gfx1151 (Gate F14)

Date: 2026-10-08
Result: **UNPATCHED PASS → PATCHED PASS — REGRESSION: NONE**

This closes the last documented Phase-3 technical condition: runtime
execution of a Kthvalue-class operation through both source-built
MIOpen variants, exercising the radix code modified by patch 0002.

## Why Kthvalue closes the patch-0002 runtime risk

Patch `0002-miopen-hiprtc-selfcontained.patch` (P3-FINAL-R3) modifies
`projects/miopen/src/kernels/radix.hpp`:

- the unconditional `#include <limits>` becomes
  `#ifdef MIOPEN_HIP_RUNTIME_COMPILE → #include "miopen_cstdint.hpp"`
  (freestanding) vs `<limits>` otherwise;
- `std::numeric_limits<int32_t>::max()` → `__INT32_MAX__` and
  `std::numeric_limits<int64_t>::max()` → `__INT64_MAX__` in `encode()`;
- (0002 also applies the same probe pattern to `tensor_view.hpp` /
  `<initializer_list>`, and 0001 to type_traits/utility wrappers — all
  three headers are included by `MIOpenKthvalue.cpp`).

`MIOpenKthvalue.cpp` — the ONLY consumer of the kthvalue radix path —
implements the entire k-th selection via radix machinery from
`radix.hpp`:

```text
line 66:  RADIX_TYPE = RadixType<DTYPE>::type
line 99:  encode<DTYPE>(input[i])              (bit-pattern ranking)
line 102: GetBitFieldImpl<RADIX_BITS>(val,pos) (digit histogram)
line 148: encode<DTYPE>(val_ori)               (candidate check)
line 160: SetBitFieldImpl<RADIX_TYPE>(...)     (desired prefix build)
```

Any defect in the patched radix path must surface in kthvalue values or
indices. Kthvalue is also the only MIOpen op whose RTC kernel reaches
`radix.hpp`'s changed `encode` at runtime on this stack, which is why
the Windows side flagged it as the residual radix consumer (Phase-3
gate 52/54 audit) and why this runtime closure was required.

## Evidence chain (all artifacts under `evidence/phase3/raw/linux/kthvalue/`)

```text
SOURCE_SHA b68f8944300f104875d953fc8e4510908c9aaf0b
  → exact patch series 0001 f06d7ae5… + 0002 77f9fc16… (P3-FINAL-R3, unmodified,
     verified from Git blobs pre-merge and post-merge, Gates F01/F04)
  → patched source tree == SOURCE_SHA + 0001 + 0002
     (re-proven by fresh forward-apply + recursive diff, Gate F06)
  → source-built unpatched libMIOpen.so.1.0 = 8694d2ba…  (archived evidence match)
  → source-built patched   libMIOpen.so.1.0 = 02904c25…  (archived evidence match)
  → public API miopenKthvalueForward (kthvalue_api.cpp:73, SOURCE_SHA signature)
  → dispatcher KthvalueForward → solver KthvalueFwd (forward_kthvalue.cpp)
  → kernel file MIOpenKthvalue.cpp, kernel KthvalueFwd
     [log proof: "Invoker registered … solver KthvalueFwd";
                 "kernel_name = KthvalueFwd, global_work_dim = {…}";
                 RTC chain LoadBinary(miss) → HIPRTC compile → SaveBinary
                 for MIOpenKthvalue.cpp.o on BOTH runs, -mcpu=gfx1151]
  → runtime result (harness exit 0, all cases PASS)
  → values + indices exactly correct vs CPU reference; A/B byte-identical
```

## Test matrix executed (identical harness binary sha256 on both sides)

| Case | Shape | dtype | dim | k | keepDim | UNPATCHED | PATCHED |
|---|---|---|---|---|---|---|---|
| FP32-2D-nokeep | {100,500} | FP32 | -1 | 10 | false | PASS | PASS |
| FP32-3D-keep-explicit-dim | {10,20,300} | FP32 | 2 | 137 | true | PASS | PASS |
| FP16-4D-keep-kmax | {8,3,10,2000} | FP16 | -1 | 2000 | true | PASS | PASS |

Per-case captured (in `run.log` + `dumps/` + `comparison.json`): input
shape, dtype, dim, k, keepDim, expected/actual values and indices (full
binary arrays), status. Inputs are fixed-seed permutation values —
pairwise distinct per slice, so the kernel's tie non-determinism note
cannot trigger and index verification is unambiguous.

## A/B comparison result (`comparison.json`)

For every case:

- input bytes identical across the two runs (same harness, same seeds);
- **output bytes and index bytes byte-identical** between unpatched and
  patched runs;
- values exactly equal CPU reference (max_abs_err = 0, exact float
  equality — no tolerance needed);
- indices exactly equal CPU reference.

Single variable between runs: which source-built `libMIOpen.so.1` was
LD_PRELOADed (dladdr-proven on the exact `miopenKthvalueForward` pointer
used, plus wrapper dladdr on `miopenCreate`); fresh isolated
`MIOPEN_CUSTOM_CACHE_DIR` per run, so no cached binary could hide
compile behavior.

## Scope honesty

This closure proves the kthvalue runtime radix path on gfx1151 with the
7.14 wheel HIPRTC stack: FP32 and FP16, contiguous innermost-dim
selection, ranks 2–4, k ∈ {10, 137, 2000}, both keepDim modes. It does
NOT claim execution of: non-applicable solver shapes (dim stride ≠ 1 or
dimSize < 300 — no MIOpen kernel path exists there), BFP16 kthvalue
(`kthvaluebfp16` exists in the driver but bfloat16 is out of gfx1151
scope here), other radix consumers that no runtime path reaches, or
other architectures (see upstream-CI follow-ups in
`findings/phase3/final_readiness/`).
