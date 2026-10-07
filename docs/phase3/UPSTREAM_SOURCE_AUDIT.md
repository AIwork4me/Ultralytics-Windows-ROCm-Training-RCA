# Phase-3 Gate 53 — Upstream Source Audit (rocm-libraries develop)

Date: 2026-10-07. Source: `C:\Users\rocm\Desktop\YOLO_AMD\rocm-libraries-phase3`
— clone of `https://github.com/ROCm/rocm-libraries`, branch `develop`
(single-branch, sparse; blobs materialized SHA1-verified via
`scripts/phase3/fetch_blobs_raw.py` after promisor fetches proved
unreliable on this network).

## Baseline provenance (recorded at clone time)

```text
remote URL:      https://github.com/ROCm/rocm-libraries.git
branch:          develop (single-branch, depth 1)
HEAD SHA:        b68f8944300f104875d953fc8e4510908c9aaf0b
HEAD subject:    feat(stinkytofu): ds_load issue cap Sliding/Periodic mode (#13093)
HEAD date:       2026-10-07 17:12:37 +0900
submodules:      none materialized (sparse checkout of projects/miopen
                 [+ rocblas/rocrand headers]; .gitmodules present at repo
                 root — MIOpen has no required submodule for this work)
verification:    every materialized file SHA1-checked against the git index
                 (fetch_blobs_raw.py); 4 symlink/LFS pointer paths remain
                 unmaterialized by design (.gitmodules, .jenkins/perf_test,
                 .lfsconfig, .readthedocs.yaml) — irrelevant to the patch
```

Raw record: `evidence/phase3/raw/source/upstream_baseline.txt`.

## The four wrapper headers — required table

| Header wrapper | RTC custom implementation? | HIP version gated? | Real STL fallback | Current concern |
|---|---:|---:|---|---|
| `miopen_type_traits.hpp` | YES (full trait shim) | YES — outer `HIP_PACKAGE_VERSION_FLAT < 7000000000ULL` disables shim for HIP>=7; inner rot window `6000025000..6001024000` gates `integral_constant/true/false/is_same/enable_if`; `enable_if` aliases `__hip_internal` | `<type_traits>` (both non-RTC and HIP>=7-RTC) | **The defect**: HIP>=7 RTC requires reachable STL; version-rotted shim unusable if re-enabled naively (Phase-2 DLL-flip falsification) |
| `miopen_utility.hpp` | YES (`std::forward` pair, via `miopen_type_traits.hpp`) | YES — same outer gate (introduced independently by `b514736610`/PR #3147; NOT part of #3803's file list) | `<utility>` (both non-RTC and HIP>=7-RTC) | Same defect class; also the #7718 mirror-failure history (shim + real STL = redefinition) |
| `miopen_limits.hpp` | YES (custom `std::numeric_limits` specializations: float/_Float16/hip_bfloat16 + `6001024024`-gated int/uchar/ushort/uint/ulong/ulonglong) | NO version gate — RTC-gated only (`MIOPEN_HIP_RUNTIME_COMPILE && !WORKAROUND_DONT_USE_CUSTOM_LIMITS`) | `<limits>` in non-RTC | RTC path already self-contained; no change needed. Residual: no `double`/signed-64 specializations — kernels' RTC usage fits current set (Gate 54) |
| `miopen_cstdint.hpp` | YES (fixed-width typedefs) | NO version gate — RTC-gated only | `<cstdint>` in non-RTC | Self-contained; no change needed |

Byte-identity check: all four develop files are IDENTICAL (modulo line
endings) to the wheel-embedded copies extracted in Phase 2
(`evidence/phase2/raw/miopen/extracted_kernel_tree/include/` +
`upstream/`) — the shipped MIOpen 3.5.2 and develop carry the same defect
logic; **the fix applies cleanly to both**.

## Gate/macro census across the kernel tree (`src/kernels`, 6474 files)

- `HIP_PACKAGE_VERSION_FLAT` users: exactly the 4 wrappers above — no
  other kernel source branches on HIP version. ✔ scope is closed.
- `MIOPEN_HIP_RUNTIME_COMPILE`: the 4 wrappers + radix.hpp (+ build-side
  files outside kernels/).
- `MIOPEN_DONT_USE_HIP_RUNTIME_HEADERS`: **zero occurrences** in the
  kernels tree (historical name from the #3803 era, since renamed).
- Direct std includes in kernels tree:
  - `<type_traits>` → miopen_type_traits.hpp only ✔ (wrapper-mediated)
  - `<utility>` → miopen_utility.hpp only ✔ (wrapper-mediated)
  - `<limits>` → miopen_limits.hpp (its own non-RTC arm) + **radix.hpp
    line 30, UNGUARDED** (but radix's `numeric_limits` USES sit inside
    `#ifndef MIOPEN_HIP_RUNTIME_COMPILE` → dead in RTC)
  - `<cstdint>` → miopen_cstdint.hpp only ✔ (wrapper-mediated)
  - `<initializer_list>` → **tensor_view.hpp line 31, UNGUARDED**, with a
    live RTC use (`tensor_layout_t(std::initializer_list<uint64_t>)`)
  - `<array>` → NOBODY (stride_array.hpp carries MIOpen's own `MyArray`
    and a `\todo Uncomment when hip RTC accepts std::array` note —
    upstream already avoided std::array in RTC by design)
- `std::` entity usage in kernel tree (comment-stripped census):
  `is_same`(16), `conditional`(16), `numeric_limits`(9), `enable_if`(8),
  `forward`(2), `is_trivially_copyable_v`(2, hip_f8_impl.hpp),
  `initializer_list`(1, tensor_view.hpp); `remove_reference/_cv` inside
  wrappers. (`std::array` matches were commented-out code only.)

## Conclusions feeding Gates 55-58

1. The wrapper pair (`miopen_type_traits.hpp` + `miopen_utility.hpp`)
   remains the right primary patch surface; limits/cstdint need no change.
2. Two residual no-STL breakers exist beyond the wrappers:
   - radix.hpp's unguarded `<limits>` include (1 kernel: MIOpenKthvalue);
   - tensor_view.hpp's unguarded `<initializer_list>` + named use
     (6 kernels: Getitem, Kthvalue, MultiMarginLoss, ReduceSum,
     SoftMarginLoss, PReLU).
   Gate 57 added canaries proving a freestanding `std::initializer_list`
   works under hiprtc/clang codegen (G57-7) and `__is_trivially_copyable`
   works in the freestanding trait set (G57-8) — so full-population
   coverage is achievable within the same design.
3. No other std machinery is reachable from RTC kernel sources in-tree
   (CK static kernels route through `miopen_utility.hpp`;
   external-CK consumers are guarded by `MIOPEN_USE_COMPOSABLEKERNEL`).
