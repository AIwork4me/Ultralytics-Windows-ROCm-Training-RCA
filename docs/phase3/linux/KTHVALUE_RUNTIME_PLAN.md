# Kthvalue Runtime Execution Plan — gfx1151 (Gate F07–F10)

Date: 2026-10-08
Branch: `rca/linux-gfx1151-phase3-regression` (post origin/main merge)
Objective: runtime-execute a Kthvalue-class operation through BOTH
source-built unpatched and patched MIOpen (P3-FINAL-R3 at SOURCE_SHA
`b68f8944300f104875d953fc8e4510908c9aaf0b`), proving the
`MIOpenKthvalue.cpp` / `KthvalueFwd` radix path — the code touched by
patch 0002 — executes correctly on both, with zero regression.

## Authoritative runtime path (derived from SOURCE_SHA sources, not assumed)

Inspected at SOURCE_SHA (baseline worktree
`~/Desktop/YOLO_AMD/rocm-libraries-linux-baseline`):

| File | Role |
|---|---|
| `projects/miopen/src/kthvalue_api.cpp` | public C entry `miopenKthvalueForward` (line 73) → `miopen::KthvalueForward` |
| `projects/miopen/src/kthvalue.cpp` | dispatcher: builds `kthvalue::FwdProblemDescription`, executes solver container `solver::kthvalue::KthvalueFwd` via `ExecutePrimitive` |
| `projects/miopen/src/solver/kthvalue/forward_kthvalue.cpp` | solver `KthvalueFwd::IsApplicable` / `GetSolution`; kernel file `MIOpenKthvalue.cpp`, kernel name `KthvalueFwd` |
| `projects/miopen/src/kernels/MIOpenKthvalue.cpp` | the device kernel; includes `radix.hpp` (`RadixType`, `encode`), `tensor_view.hpp`, `miopen_type_traits.hpp` — all headers modified by patch series P3-FINAL-R3 |
| `projects/miopen/driver/kthvalue_driver.hpp` | official driver semantics: input gen, CPU reference `mloKthvalueFwdRunHost`, CLI flags |
| `projects/miopen/driver/dm_kthvalue.cpp` | driver dtype dispatch: `kthvalue` (FP32), `kthvaluefp16`, `kthvaluebfp16` |
| `projects/miopen/test/gtest/kthvalue.hpp` | upstream gtest cases (representative shapes) |

Solver applicability (`forward_kthvalue.cpp`): `IsImprovementOverROCm`
requires rank ≥ 2, selected-dim stride == 1 (innermost), dim size ≥ 300;
plus rank ≤ 5. All planned cases satisfy this so the MIOpen kernel — not
any fallback — executes.

The kernel is RTC-only: no `KthvalueFwd` entry exists in any kernel DB
shipped in the source-built install (`share/miopen/db/gfx115128*`
checked — no Kthvalue). A fresh empty `MIOPEN_CUSTOM_CACHE_DIR` therefore
forces a runtime HIPRTC compile of `MIOpenKthvalue.cpp` on first call.

## Execution mechanism (Gates F08/F09 decision)

`MIOpenDriver` was not built (`MIOPEN_BUILD_DRIVER=OFF` in the validated
builds) and enabling it would reconfigure the validated library build —
an invasive change. Per the preference order, a **minimal C++ runtime
harness** is used (Option B, Gate F09):

- calls the public API `miopenKthvalueForward` with the exact SOURCE_SHA
  signature `(handle, inputDesc, input, outputDesc, output, indicesDesc,
  size_t* indices, size_t k, int32_t dim, bool keepDim)`;
- allocates GPU buffers via the HIP runtime (`hipMalloc`/`hipMemcpy`/
  `hipDeviceSynchronize`) resolved from the same wheel ROCm stack the
  validated builds use;
- resolves ALL MIOpen and HIP symbols via `dlsym(RTLD_DEFAULT)` and
  proves library binding with `dladdr` on the exact function pointers
  used (not merely `miopenCreate`), printing resolved DSO paths;
- loads the source-built library via the already-proven mechanism from
  the prior validation: `LD_PRELOAD` of the install's `libMIOpen.so.1`
  (wheel dlopen-by-absolute-path makes `LD_LIBRARY_PATH` insufficient —
  established in Phase-3 Linux evidence) using
  `scripts/phase3/linux/run_with_source_miopen.sh`;
- uses a fresh isolated `MIOPEN_CUSTOM_CACHE_DIR` + `XDG_CACHE_HOME` per
  run (wrapper does this);
- runs with `MIOPEN_ENABLE_LOGGING=1`, `MIOPEN_LOG_LEVEL=6`,
  `MIOPEN_ENABLE_LOGGING_CMD=1` so solver selection, kernel-name, and
  RTC compile of `MIOpenKthvalue.cpp` appear in the archived log —
  kernel execution is NOT inferred from API return alone;
- compares values AND indices against an in-harness CPU reference that
  mirrors the official driver reference `mloKthvalueFwdRunHost`
  (per-slice sort by value, answer = k-th smallest, index = its position
  within the dim).

PyTorch `torch.kthvalue` is NOT used: no evidence exists that it
dispatches to `miopenKthvalueForward` (PyTorch ships its own GPU
kthvalue), and the mission forbids assuming it.

## Deterministic test cases (Gate F10)

Input construction: each dim-slice is a fixed-seed xorshift
Fisher–Yates **permutation** of `{0..n-1}` mapped to
`value = base + 0.25 * perm[j]` with `base` centered per dim size.
Consequences: **all values within a slice are pairwise distinct by
construction** (no tie ambiguity — the driver's tie non-determinism note
in `MIOpenKthvalue.cpp` case-2 cannot trigger), values are exactly
representable in FP32 and FP16, and inputs are byte-identical across
runs (fixed seeds, no PRNG state carried across processes).

| # | shape | dtype | dim | k | keepDim | mirrors upstream gtest |
|---|---|---|---|---|---|---|
| 1 | {100, 500} | FP32 | -1 (innermost) | 10 | false | `{100,500}, k=10` |
| 2 | {10, 20, 300} | FP32 | 2 (explicit innermost) | 137 | true | `{10,20,300}` shape (k made nontrivial) |
| 3 | {8, 3, 10, 2000} | FP16 | -1 | 2000 (max) | true | `{8,3,10,2000}, k=2000` |

Case 3 adds the FP16 dtype (second dtype relevant to the changed radix
`encode<DTYPE>` / `RadixType<DTYPE>` code, per driver `kthvaluefp16`),
exercising the radix path's half-precision encode. BFP16 is excluded:
no bfloat16 GPU support is claimed for gfx1151 in scope of this
validation and FP16 already covers the "second dtype" requirement.

Captured per case: input shape, dtype, dim, k, keepDim, full expected
values/indices (CPU), full actual values/indices (GPU), per-case and
overall status, all archived under
`evidence/phase3/raw/linux/kthvalue/{unpatched,patched}/`.

## Verification semantics

- Values: exact equality (inputs are exact 0.25-multiples; radix
  encode/decode is bitwise for exactly-representable values; CPU and GPU
  both select from the same distinct input set, so equality is expected
  bit-exact, not tolerance-based).
- Indices: exact equality against the CPU reference (unique answer per
  slice because all values are distinct).
- A/B: identical harness binary, identical input bytes, identical
  options; only variable = which source-built libMIOpen.so.1 is
  LD_PRELOADed (unpatched `8694d2ba…` vs patched `02904c25…`).

## Success criteria

```text
UNPATCHED: all cases PASS (values + indices)
PATCHED:   all cases PASS (values + indices)
REGRESSION: NONE
```

A patched-side failure with unpatched PASS is recorded as
`KTHVALUE_RUNTIME_REGRESSION_DETECTED` and reported without fixing the
patch.
