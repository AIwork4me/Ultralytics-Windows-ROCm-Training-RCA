# Phase-2 Runtime STL Requirements (Gates 29 & 31)

Date: 2026-10-07. Local raw evidence: `evidence/phase2/raw/miopen/`
(extracted kernel tree + STD_INVENTORY.txt), `evidence/phase2/raw/candidateB/`.
Upstream artifacts fetched read-only into the session temp and cited by URL.

## 1. The exact compile unit that fails

MIOpen extracts from `MIOpen.dll` (embedded string table) into a comgr temp
dir and HIPRTC-compiles (captured live with `AMD_COMGR_SAVE_TEMPS=1`,
cache-isolated run — archived at
`evidence/phase2/raw/miopen/extracted_kernel_tree/`):

```text
input/MIOpenBatchNormFwdTrainSpatial.cpp
include/  (158 headers, the full embedded kernel-header set)
```

### Quoted-include reachability closure of the failing kernel (13 files)

```text
MIOpenBatchNormFwdTrainSpatial.cpp
├─ batchnorm_functions.hpp
│  ├─ configuration.hpp
│  │  ├─ default_configurations.hpp
│  │  ├─ vector_types.hpp ──► miopen_type_traits.hpp ──► #include <type_traits>  ← FAILS
│  │  └─ bfloat16_dev.hpp
│  └─ miopen_math.hpp
├─ activation_functions.hpp
├─ bnorm_spatial_activation_functions.hpp (via .cpp line 9 in wheel; line 30 in develop)
├─ reduction_functions.hpp (wheel)
├─ static_unroll.hpp
└─ float_types.h
```

### Angle-includes actually reached from the closure

- HIP headers (`hip/hip_runtime.h`, `hip/hip_fp16.h`,
  `hip/amd_detail/*` …) — resolved by hiprtc/comgr internals (empirically:
  compiles proceed past them).
- **`<type_traits>` — the single non-HIP standard header in the BN closure.**

`<utility>`, `<limits>`, `<cstdint>`, `<initializer_list>` (the other std
directives found in the 158-header embedded set) are NOT in the BN closure —
they belong to other kernels' headers (composable-kernel `functional*.hpp`
etc.). Lead D's "next header fails" concern is therefore empirically
answered for BN: fixing `type_traits` alone closes the BN path (validated in
Gate 32: all BN variants pass with a type_traits-only shim).

## 2. std functionality actually used by the BN closure

| Entity | Used in (extracted wheel headers) | Status in historical shim |
|---|---|---|
| `std::conditional` | `configuration.hpp`, `MIOpenBatchNormFwdTrainSpatial.cpp` (2 sites) | defined (outside version window) ✓ |
| `std::is_same` | `vector_types.hpp` | **only in HIP 6.0.25–6.1.24 window** ✗ |
| `std::enable_if` | `bnorm_spatial_activation_functions.hpp` (+`enable_if_t`?) | **only in window, via `__hip_internal::enable_if`** ✗ |
| `std::remove_reference` | `miopen_type_traits.hpp` (self) | defined ✓ |
| `std::remove_cv` | `miopen_type_traits.hpp` (self) | defined ✓ |
| `std::is_pointer` | `miopen_type_traits.hpp` (comment/self) | defined via `is_pointer_helper : false_type` — **depends on window-gated `false_type`** ✗ |
| `true_type`/`false_type`/`integral_constant` | shim internals | window-gated ✗ |

Verdict: the closure needs a freestanding `type_traits` providing
`integral_constant`, `true_type`, `false_type`, `remove_reference[_t]`,
`remove_const`, `remove_volatile`, `remove_cv[_t]`, `is_same`,
`enable_if[_t]`, `is_pointer`, `conditional[_t]` — 48 lines
(`patches/shim_stl/include/type_traits`, validated end-to-end in Gate 32).

## 3. The upstream gate logic (authoritative sources)

### Wheel-embedded `miopen_type_traits.hpp` (extracted; identical structure to develop)

```cpp
#if HIP_PACKAGE_VERSION_FLAT < 7000000000ULL     // HIP < 7.0
#ifdef MIOPEN_HIP_RUNTIME_COMPILE                // runtime-compile mode
namespace std { /* …no-STL shim… */ }            // self-contained
#else
#include <type_traits>                           // offline: real STL
#endif
#else                                             // HIP >= 7.0
#include <type_traits>                           // ALWAYS real STL (← defect)
#endif
```

`miopen_utility.hpp` carries the same outer gate for `<utility>`;
`miopen_limits.hpp` uses `WORKAROUND_DONT_USE_CUSTOM_LIMITS` (RTC mode gets
a custom limits shim for this HIP version, so `<limits>` is not required in
the BN closure); `miopen_cstdint.hpp` gates on RTC mode alone.

### Where the gate came from (two separate upstream commits — attribution corrected per Gate-45 review)

- **`miopen_type_traits.hpp`**: commit
  `ce14dab3b92a82aca14c3477619157f41928fe99` (PR **ROCm/MIOpen#3803**
  "All 7.0 hipRTC fixes", merged 2025-06-16) added the outer
  `#if HIP_PACKAGE_VERSION_FLAT < 7000000000ULL` wrapper; the exact 4-line
  diff is archived at `evidence/phase2/raw/upstream/commit_ce14dab3.json`.
  NOTE (post-review): that commit's context shows the inner macro as
  `MIOPEN_DONT_USE_HIP_RUNTIME_HEADERS`; the wheel and current develop use
  `MIOPEN_HIP_RUNTIME_COMPILE` — a later rename. The wheel header is
  therefore not byte-identical to ce14dab3's immediate product; the outer
  version gate itself is unchanged.
- **`miopen_utility.hpp`**: commit `b514736610` (PR **#3147**, 2025-12-18,
  "[MIOpen] Update include to use utility if hip version > 7.0"; body:
  "With 7.0 the previous workarounds to declare std types is no longer
  valid (and causes hipRTC failures). This should resolve one of the
  issues found in #2617.") added the same outer gate for `<utility>`
  INDEPENDENTLY of #3803 (the #3803 file list does not include
  miopen_utility.hpp). Archived at
  `evidence/phase2/raw/upstream/commit_b514736610.json`.
- Why HIP 7.0 needed changes (ROCm/clr `hipamd/src/hiprtc/hiprtc.cpp`):
  hiprtc's builtin header (`hiprtc_runtime.h`, force-included with
  `-D__HIPCC_RTC__ -nogpuinc`) previously **defined `std` type traits**,
  conflicting with consumers' own definitions; in 7.0 they were moved to
  `__hip_internal` — after which RTC consumers must include the real STL.
  (`--hiprtc-no-builtin-header` existed for the conflict era; the source
  comment says it "can be removed" once traits moved — i.e., AMD's 7.0
  design direction is real-std-headers in RTC sources.)
- `hipamd/src/hiprtc/hiprtcInternal.cpp`: on `_WIN32`, hiprtc pushes
  `-target x86_64-pc-windows-msvc -fms-extensions -fms-compatibility` and
  **no C++ stdlib include path** — Windows std-header resolution is left
  entirely to clang's MSVC toolchain auto-detection (registry/vswhere) or
  caller-supplied `-I`.
- MIOpen `src/comgr.cpp` `BuildHip()`: adds
  `-D__HIP_PLATFORM_AMD__=1 -DHIP_PACKAGE_VERSION_FLAT=<v>
  -DMIOPEN_HIP_RUNTIME_COMPILE … -std=c++17` and
  **`-I$ROCM_PATH/include` only if the `ROCM_PATH` env var is set**
  (log string `"HIPRTC compile ROCm include path argument"` present in the
  shipped 3.5.2 rockrel DLL; runtime honoring proven by the Gate-32
  poisoned-header experiment).

## 4. Platform asymmetry that created the regression window

| Platform | HIP≥7.0 RTC std-header resolution | Effect |
|---|---|---|
| Linux | clang default search finds system libstdc++/libc++ (`/usr/include/c++/…`) | MIOpen #3803's assumption holds |
| Windows + TheRock-style build env | MSVC toolchain present (TheRock docs: MSVC 19.43+ is a build prerequisite) | assumption holds incidentally |
| **Windows + rockrel pip wheels, no MSVC** | wheel ships no STL; clang search = resource dir + legacy VS8/9/10 fallback dirs | **assumption fails → this RCA's defect** |

Corroboration: rocm-libraries #2169's TheRock-built Windows log compiled
past the include chain (external evidence, C025 — machine may have had VS
installed; not locally provable). MIOpen #3956 (gfx1200/ROCm 7.2.1/Py3.12)
shows the same failure signature as ours on stock installs (external,
C022).

## 5. Candidate fixes evaluated (Gate 30 → results in Gate 32)

| Candidate | Layer | Phase-2 result |
|---|---|---|
| A — host STL discovery (provide/discover an STL for HIPRTC) | wheel packaging / environment | **VALIDATED 3 ways**: (1) MSVC Build Tools install → clang auto-discovery, plain shell — all BN cases pass; (2) `INCLUDE`-only injection — pass; (3) `ROCM_PATH` → `-I` shim dir (48-line freestanding `type_traits`, no MSVC) — all BN cases pass cache-isolated. `-I$ROCM_PATH/include` proven honored and shadowing MSVC. |
| B — MIOpen runtime-safe shims (self-contained RTC kernels) | MIOpen source | **principally validated**: freestanding-shim content compiles+runs the real kernels through the real MIOpen path (via A-3's mechanism). The *historical* embedded shim is rotted (see D). Upstream PR shape: make the shim's traits unconditional in RTC mode and define `enable_if` properly (not via `__hip_internal`). |
| C — header-specific `__HIPCC_RTC__` guards | MIOpen source | Subsumed by B (same edits); the guard pattern `#if !defined(__HIPCC_RTC__) #include <utility> #endif` would work for non-trait headers; for traits the shim content is still required. |
| D — revise the HIP≥7.0 version gate | MIOpen source | **Naive form FALSIFIED by experiment**: length-preserving DLL patch `<7000000000ULL` → `<8000000000ULL` (2 sites; original SHA256 `74b4ee03…`, restored and verified after) makes HIP 7.14 take the shim branch — compile still fails: `miopen_type_traits.hpp:112 expected class name` (`false_type` undefined) + `no template named 'enable_if' in namespace 'std'` — the shim's trait block is gated to the 6.0.25–6.1.24 window and its `is_pointer_helper` depends on window-gated `true/false_type`. **A version-gate change alone is insufficient; the shim itself must be repaired.** (Also the brief's warning that the old shim depends on version-specific HIP behavior — here `__hip_internal::enable_if` — is confirmed.) |
