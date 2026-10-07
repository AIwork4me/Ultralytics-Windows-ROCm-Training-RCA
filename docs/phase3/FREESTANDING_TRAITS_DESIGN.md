# Phase-3 Gate 56 — `namespace std` Risk Analysis (FREESTANDING_TRAITS_DESIGN)

Date: 2026-10-07.

## Why this analysis exists

The historical MIOpen compatibility shims inject definitions into
`namespace std` — technically UB for user code ([namespace.std]/1: adding
declarations to std is undefined unless specified). Reviewer-C flagged
this ("reviving namespace std definitions is technically UB and was the
source of the original hiprtc builtin-header conflicts that #3803 was
reacting to"). Gate 56 must show the revived shim cannot collide, or move
it out of std.

## The five questions

### 1. Does HIPRTC already define overlapping entities?

Era-dependent — this is the crux of the historical gates:

- **HIP < 6.0.25**: hiprtc's force-included builtin header
  (`hiprtc_runtime.h`, via `-D__HIPCC_RTC__ -nogpuinc`) did NOT provide
  std traits; MIOpen's original shim was created for exactly this gap.
- **HIP 6.0.25–6.1.24**: the builtin header DID define std traits →
  MIOpen's inner window gate exists solely to alias
  `std::enable_if = __hip_internal::enable_if` instead of defining it
  (Phase-2 DLL-flip experiment proved this concretely: naive re-enable of
  the shim on HIP 7.14 died at `false_type` undefined — the window gate —
  and on `__hip_internal::enable_if`).
- **HIP ≥ 7.0**: clr moved the builtin traits to `__hip_internal`
  (`hipamd/src/hiprtc/hiprtc.cpp`, archived
  `evidence/phase2/raw/upstream/hiprtc_clr.cpp`): RTC consumers are
  EXPECTED to include the real STL; `namespace std` is no longer populated
  by hiprtc itself. **On HIP ≥ 7 the std namespace inside an RTC
  translation unit starts empty** → our freestanding definitions cannot
  collide with hiprtc-provided ones. (Canary G57-3 verifies on 7.14.)

### 2. Can the custom definitions collide with anything else?

Only if a *real* std header is also reachable in the same TU. Both
coexistence channels are closed by Design D's availability probe:

- The freestanding branch is selected only when `__has_include(<type_traits>)`
  is false — i.e. the real header does not resolve anywhere on the search
  path, so nothing else can have included it either (any `#include <type_traits>`
  elsewhere in the TU would itself have failed, since include resolution is
  TU-global, not per-include-site).
- Conversely, when real STL is reachable the freestanding header is never
  entered, so MIOpen cannot be the collision source. This also structurally
  prevents the #7718 failure class (MSVC ≥14.43 + older MIOpen where the
  utility shim coexisted with MSVC's real `<utility>` → `std::forward`
  redefinition): coexistence requires the shim to be active while real STL
  resolves — exactly the state the probe makes unreachable.

Residual theoretical channel: a *different freestanding* std-subset (e.g.
another vendored header defining `std::is_same`) on the search path. Not
present in the MIOpen kernel tree (Gate 54 audit enumerates all std
definitions); rocRAND's vendored `rocrand_xorwow.h` (inlined into MIOpen)
post-#8247 guards its `<utility>` include with `__HIPCC_RTC__` and defines
nothing in std.

### 3. Was the namespace-std injection the reason for the HIP 7 changes?

Partly, but not for collision-freedom of its own: #3803 ("All 7.0
hipRTC fixes") and #3147 ("the previous workarounds to declare std types
is no longer valid (and causes hipRTC failures)… resolves one of the
issues found in #2617") removed the shims because hiprtc 7.0's design
direction made real std headers THE supported mechanism (traits moved to
`__hip_internal`, `--hiprtc-no-builtin-header` era over). The removal was
a simplification under the assumption "RTC consumers have an STL" — true
on Linux/TheRock, false on stock Windows wheels (this RCA). The change
was not fixing a namespace-std collision on Windows; it was dropping
machinery believed obsolete.

### 4. Can the compatibility types live in another namespace?

Not without touching every consumer. Kernel sources reference literal
`std::conditional`, `std::is_same`, `std::enable_if_t`, `std::forward`…
spread across `vector_types.hpp`, `configuration.hpp`,
`bnorm_spatial_activation_functions.hpp`, CK `functional*.hpp` wrappers,
etc. (Gate 54 matrix). Moving definitions to `miopen_std::` + aliasing
(`namespace std { using miopen_std::is_same; }`) still injects into std —
same UB surface with more moving parts. Renaming all use sites is a
large-diff kernel-tree-wide change: maximal regression surface, rejected.

### 5. Do kernels require literal std:: names? Would aliases be safer?

Yes (see 4); per-entity `using`-aliases are the "safer" variant of the
same injection and buy nothing over direct definitions while doubling the
definition sites. Rejected.

## Design decision (freestanding traits)

1. **Keep `namespace std` injection, scoped to the no-STL arm only**
   (Design D). UB-on-paper but 10+ years of MIOpen practice (HIP 5/6 era),
   bounded by the probe, and the only shape that fixes kernels without
   editing them. This mirrors what the rocRAND fix (#8247) accepted for
   its own vendored code.
2. **Dedicated headers** (`miopen_freestanding_type_traits.hpp`,
   `miopen_freestanding_utility.hpp`): no version windows, no
   `__hip_internal` dependencies, `#pragma once`, containing:
   - a self-test block of `static_assert`s (compiled in the canaries and
     in the new no-STL CI test), and
   - a co-inclusion guard: `#ifdef MIOPEN_FREESTANDING_TRAITS_ACTIVE`
     set by the wrapper after including it, so accidental double
     inclusion through both wrappers is idempotent (the traits header is
     also directly include-safe for the utility header's dependency).
   Real-STL coexistence is prevented upstream of the guard by the probe;
   the guard covers only freestanding-with-freestanding.
3. **Legacy HIP<7 branch left byte-identical** — its rotted windows are
   load-bearing for historical hiprtc behavior; touching them has zero
   upside for the defect being fixed and unbounded downside.
4. `enable_if` defined properly (primary template + `true`
   specialization), never via `__hip_internal` — that import was the
   6.x-window bridge and is invalid on HIP≥7 where our new arm runs.

## Canary obligations (discharged in Gate 57)

- G57-1: freestanding headers compile `-nostdinc` under
  `MIOPEN_HIP_RUNTIME_COMPILE` + `HIP_PACKAGE_VERSION_FLAT=7140060850ULL`,
  gfx1151, static_asserts pass, kernel EXECUTES.
- G57-2: probe semantics — `__has_include(<type_traits>)` false under
  `-nostdinc`, true in default env; both directions observed.
- G57-3: no redefinition when freestanding path is taken (std starts
  empty on HIP≥7 RTC — compile a TU defining/using all shim entities).
- G57-4: wrapper-gated behavior — the WRAPPER (not the bare header)
  selects real vs freestanding vs legacy per defines, for both
  `miopen_type_traits.hpp` and `miopen_utility.hpp`.
