# Phase-3 Gate 55 — Candidate Patch Design

Date: 2026-10-07. Status: design *before* implementation (per gate rules).
Inputs: Phase-2 LEVEL-3 RCA, Reviewer-C guidance (`subagent_upstream_readiness_review.md`
§3.6/§5), upstream archaeology (`evidence/phase2/raw/upstream/`), Gate-70
research (2026-10-07): rocm-libraries#7718 (MSVC ≥14.43 + older MIOpen →
`std::forward` REDEFINITION — the mirror failure), rocPR/rocrand precedent
rocm-libraries PR #8247 (guard `<utility>` with `__HIPCC_RTC__`), TheRock
PR #3588 (ship llvm C++ headers in build artifacts), MIOpen#3956 (this
defect, gfx1200/7.2.1).

## The property to restore

> MIOpen runtime-compiled (HIPRTC) kernel sources must compile without a
> host C++ standard library, on every platform and HIP version, without
> regressing environments where a real STL is present.

## Observed constraint matrix (evidence-backed)

| Environment | Today (develop) | Requirement |
|---|---|---|
| Linux, any HIP, RTC | real STL (reachable) | must keep working |
| Windows wheel, no MSVC, HIP≥7 RTC | **hard failure** (this RCA) | must compile (shim) |
| Windows wheel, MSVC present, HIP≥7 RTC | real STL via auto-discovery | must keep working |
| Windows, MSVC ≥14.43, HIP<7-era shim active (#7718) | `std::forward` redefinition failure | shim + real STL must never coexist |
| HIP<7 RTC (all platforms) | legacy shim (rotted windows) | keep behavior (don't touch) |
| Offline/non-RTC builds | real STL | unchanged in all designs |

Key insight from #7718 + #3803 archaeology: the failure is BIDIRECTIONAL.
A design that activates the shim unconditionally in RTC mode reintroduces
the #7718 collision class wherever a real STL is reachable. A design that
requires real STL unconditionally (today's develop) fails wherever it is
not. The correct discriminator is neither HIP version nor RTC mode alone
but **std-header availability**: use the real STL when it resolves, the
freestanding implementation when it does not.

## Design A — RTC-mode discriminator (restore pre-#3803 semantics)

```cpp
#ifdef MIOPEN_HIP_RUNTIME_COMPILE
/* freestanding shim in namespace std */
#else
#include <type_traits>
#endif
```

- Correctness: restores pre-#3803 property; historically worked (HIP 5/6 era).
- **Fatal flaw (Linux regression risk)**: post-#3803 kernels may use traits
  beyond the shim subset (`std::is_trivially_copyable_v` already appears in
  the embedded kernel tree). Taking the shim on Linux HIP≥7 replaces a
  working real-STL compile with a possibly-incomplete shim → new hard
  failures on the primary supported platform. Reviewer-C B3.
- **Fatal flaw (#7718 class)**: shim `std::forward` + reachable real STL in
  the same TU (other headers pulling real `<utility>`) → redefinition, on
  Windows-with-MSVC and potentially Linux.
- Rejected: not defensible as low-risk.

## Design B — dedicated freestanding headers, RTC discriminator

Same gating as A but shim content lives in new
`miopen_freestanding_type_traits.hpp` / `miopen_freestanding_utility.hpp`
with `static_assert` self-tests, included by the wrappers in RTC mode.

- Better ownership/testability than A (Reviewer-C's preference in
  structure), but inherits BOTH fatal flaws of A (same discriminator).
- Rejected as-is for the same reasons.

## Design C — runtime-compiler STL provisioning (packaging layer)

Make MIOpen/hiprtc discover or package a std library (TheRock wheel-side:
bundle freestanding std subset, export via `-I`). Also viable: document
MSVC as prerequisite.

- This is the *wheel/packaging/docs* layer fix — NOT a rocm-libraries
  MIOpen PR. Different owners (TheRock / ROCm docs). Out of scope for the
  MIOpen patch; recorded in the routing plan (Gate 80).
- Not chosen as the MIOpen patch, per layer ownership.

## Design D — availability probe (selected)

Keep the existing structure; replace only the HIP≥7 RTC sub-decision with
an std-header availability probe:

```cpp
// miopen_type_traits.hpp (sketch; utility analogous)
#ifdef MIOPEN_HIP_RUNTIME_COMPILE
#if HIP_PACKAGE_VERSION_FLAT < 7000000000ULL
    /* legacy pre-7 shim — UNCHANGED (rotted windows are historical HIP<7
       behavior; hiprtc<7 builtin header conflicts make real STL unsafe) */
#elif __has_include(<type_traits>)
#include <type_traits>      /* real STL reachable (Linux, Windows+MSVC):
                                byte-identical behavior to today's develop */
#else
#include "miopen_freestanding_type_traits.hpp"  /* no STL anywhere: new path */
#endif
#else
#include <type_traits>      /* offline builds: unchanged */
#endif
```

Rationale per comparison axis:

- **Correctness**: every environment keeps its today-behavior except the
  one that hard-fails today (no reachable STL), which gains a freestanding
  implementation. No environment that works today changes behavior at all
  (Linux: `__has_include` true → real; Windows+MSVC: true → real; HIP<7:
  untouched; offline: untouched).
- **Scope**: two wrapper files edited + two new freestanding headers;
  `miopen_limits.hpp`/`miopen_cstdint.hpp` already RTC-gated without
  version gates (audit confirms; no change expected).
- **Platform independence**: no platform macros at all; the probe is a
  compiler feature (`__has_include` is C++17-standard, supported by clang
  ≥5, MSVC ≥19.11 — and only ever evaluated inside the RTC branch, which
  host compilers never take; hiprtc is clang-backed on both platforms).
- **Risk**: the only new compile path executes where compilation
  previously ALWAYS failed — a strictly-better transform. The #7718
  coexistence hazard cannot trigger: the freestanding path is selected only
  when `<type_traits>`/`<utility>` do not resolve anywhere.
- **Maintenance**: freestanding headers are self-tested
  (`static_assert`s), additive, and not version-gated; new kernels needing
  new traits extend them without touching the wrappers.
- **Compatibility**: HIP<7 branch byte-identical; HIP≥7-with-STL branch
  identical to develop; non-RTC identical.
- **Testability**: each branch is directly testable —
  `-nostdinc` (no-STL arm), default env (STL arm), `-DMIOPEN_HIP_RUNTIME_COMPILE`
  off (offline arm) — exactly the canary matrix of Gate 57.

### Freestanding content scope (initial, from Gate 54 audit + Phase-2 closure)

`integral_constant, true_type, false_type, remove_reference[_t],
remove_const, remove_volatile, remove_cv[_t], is_same, enable_if[_t],
is_pointer, conditional[_t]` (type_traits) and `forward` (utility) —
final scope confirmed by the Gate 54 RTC×std-entity matrix; the headers
grow to cover exactly what the audit finds (Windows-wheel kernels beyond
coverage keep today's failure mode, i.e. no regression, just unfixed —
documented in the routing plan as the wheel-layer residual).

### Precedent

rocRAND solved the same class in-tree with `__HIPCC_RTC__` guards
(rocm-libraries PR #8247, merged 2026-07-11) rather than version gates —
in-project self-containment is an accepted upstream pattern. Our
`MIOPEN_HIP_RUNTIME_COMPILE` plays the same role as their `__HIPCC_RTC__`,
with the availability probe additionally preserving the real-STL path
post-#3803 kernels now rely on.

## Decision

**Design D** (dedicated freestanding headers + HIP<7 legacy shim + HIP≥7
availability probe). Design B's file organization with a corrected
discriminator. Design A rejected (Linux regression + #7718 class);
Design C routed to the packaging layer (Gate 80).

Residual risks to validate in Gates 57–68 (not design blockers):
1. `__has_include` behavior under hiprtc 7.14/comgr on gfx1151 (canary).
2. hiprtc builtin header must not itself define probed/`std` traits for
   HIP≥7 (moved to `__hip_internal` in 7.0 per clr archaeology; canary
   re-verifies on 7.14).
3. Other RTC kernels' std usage beyond the shim set remains broken on
   no-STL Windows (wheel-layer residual; Gate 68 quantifies).
