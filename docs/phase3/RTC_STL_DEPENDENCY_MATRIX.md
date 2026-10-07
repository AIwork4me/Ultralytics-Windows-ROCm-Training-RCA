# Phase-3 Gate 54 — RTC Kernel × std-Dependency Matrix

Date: 2026-10-07. Generator: `scripts/phase3/audit_rtc_std_dependencies.py`
(reusable, committed). Raw output:
`evidence/phase3/raw/source/rtc_std_dependency_matrix.json`.
Input tree: rocm-libraries develop `b68f8944` `projects/miopen/src/kernels`
(6474 files). Define set evaluated: `MIOPEN_HIP_RUNTIME_COMPILE=1`,
`HIP_PACKAGE_VERSION_FLAT=7140060850` (the defect condition).

## Method

- RTC population: all 104 `*.cpp` kernel entry files under `src/kernels`
  (incl. `static_composable_kernel/src/kernel_wrapper/*` and
  `gpu_reference_kernel/*`). These are the translation units MIOpen embeds
  and can hand to HIPRTC at runtime (`add_kernels` embeds the same set the
  build registers; the wheel's embedded 158-header include set confirms the
  mechanism).
- Per entry: quoted-include closure (BFS) over the kernel header set with
  a preprocessor state that evaluates the load-bearing conditionals under
  the RTC define set (`#if/#ifdef/#elif/#else` honored; `__has_include`
  counted as reachable — the real-STL case).
- std entities: regex over ACTIVE lines only (commented code excluded —
  important: `stride_array.hpp`'s `std::array` uses are commented out).

## Results

### std-header reachability from RTC closures (before patch)

| std header | kernels whose closure reaches it | route | covered by |
|---|---:|---|---|
| `<type_traits>` | 32 | `miopen_type_traits.hpp` wrapper (HIP>=7 arm) | **V1 wrapper probe** |
| `<utility>` | 14 | `miopen_utility.hpp` wrapper (HIP>=7 arm) | **V1 wrapper probe** |
| `<initializer_list>` | 6 | `tensor_view.hpp:31` direct, unguarded, LIVE use | residual (V2 scope) |
| `<limits>` | 1 (MIOpenKthvalue) | `radix.hpp:30` direct, unguarded; uses dead in RTC | residual (V2 scope) |
| `<cstdint>` | 0 direct | `miopen_cstdint.hpp` mediates | already self-contained |
| `<array>` | 0 | only commented-out uses + `MyArray` replacement exists | none needed |

### std entities referenced in active RTC closure code

| Entity | entries | provider after patch |
|---|---:|---|
| `std::is_same` | 17 | freestanding type_traits (no-STL) / real (STL) |
| `std::conditional` | 16 | same |
| `std::forward` | 14 | freestanding utility / real |
| `std::numeric_limits` | 5 | `miopen_limits.hpp` custom class in RTC (unchanged; float/int/etc. specializations match usage incl. `lowest()` for float) |
| `std::initializer_list` | 6 | freestanding initializer_list (V2) / real |
| `std::is_trivially_copyable_v` | 2 (hip_float8.hpp → MIOpenSoftmaxAttn, MIOpenCheckNumerics) | freestanding type_traits via `__is_trivially_copyable` builtin (added; canary G57-8) |
| `std::enable_if`, `remove_reference`, `remove_cv`, `true/false_type`, `integral_constant`, `is_pointer` | wrapper + BN closure set | freestanding type_traits |

### Distinguishing included / referenced / instantiated / runtime-path-relevant

- *included*: the header is reachable through the closure's active
  preprocessor branches (table above).
- *referenced*: entity appears in active code of the closure (table
  above). A referenced entity is not necessarily *instantiated* (e.g.
  templates inside dead `if constexpr(0 || 0)` branches still parse but
  don't instantiate — warnings in the BN compile log show such branches).
- *instantiated*: guaranteed only for entities appearing in emitted
  device code; e.g. `is_trivially_copyable_v` fires from `static_assert`
  inside `bit_copy<T>` — instantiated when f8 conversion kernels are
  compiled (MIOpenSoftmaxAttn f8 paths).
- *runtime-path relevant*: an RTC entry only compiles at runtime when a
  solver selects that kernel for the executed op+arch+dtype (BN spatial:
  yes for every `BatchNorm2d/3d` train/infer on gfx1151 without fused
  inference — Phase-1/2 established; Getitem/PReLU/Kthvalue/etc.: workload
  dependent).

### The BN closure (the RCA defect path)

13 files, single non-HIP angle-include `<type_traits>` via the wrapper —
verified by compile: patched tree + `-nostdinc` → exit 0, code object
5792 B; pristine tree + `-nostdinc` → `miopen_type_traits.hpp:151: fatal
error: 'type_traits' file not found` (exact original signature).
`evidence/phase3/raw/source/bn_compile_{patched_nostdinc,patched_defaultenv,baseline_nostdinc}.json`.

## Conclusions

1. V1 (wrapper pair + 3 freestanding headers) covers 32+14 kernels —
   including the entire BatchNorm family (the RCA defect) and the static
   CK conv wrappers.
2. Two small residuals keep 6+1 kernels broken in no-STL environments
   (Kthvalue, Getitem, MultiMarginLoss, ReduceSum, SoftMarginLoss, PReLU
   — via tensor_view; Kthvalue also via radix). Their fix shapes are
   canary-validated (`initializer_list` layout works with clang codegen;
   radix's RTC arm uses nothing from `<limits>`) — folded into the final
   scope decision at Gate 76 (V2).
3. No RTC kernel needs `std::array` (upstream replaced it with `MyArray`,
   with an in-tree TODO documenting why).
4. `miopen_limits.hpp` / `miopen_cstdint.hpp` require no change (already
   RTC-self-contained; audit confirms usage fits their specializations).
