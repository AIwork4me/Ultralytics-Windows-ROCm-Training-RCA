# Phase-3 Gate 83 — Reviewer B (falsification specialist)

Date: 2026-10-07. Mandate: find a platform/HIP-version/kernel/code-path
the patch could break. Proven by live compilation with the wheel clang
where stated.

## Verdict: BREAKAGE FOUND — 1 BLOCKER, 1 conditional MAJOR, minors

1. **BLOCKER — radix.hpp RTC arm removes the only `std::numeric_limits`
   provider in the MIOpenKthvalue.cpp TU; kthvalue fails to RTC-compile
   on EVERY platform — including a mainline Linux HIP>=7 regression.**
   - Pre-patch: `#include <limits>` unconditional → worked wherever
     `<limits>` resolved (all Linux).
   - Post-patch: RTC arm has no numeric_limits declaration; `encode()`'s
     `std::numeric_limits<int32_t/int64_t>::max()` are NON-DEPENDENT
     names in discarded `if constexpr` branches → checked at
     template-definition PARSE time (the design docs' "dead in RTC"
     dismissal is false C++ semantics).
   - **Live proof** (wheel clang, real patched files, both default env
     and -nostdinc): `radix.hpp:74/78: error: no member named
     'numeric_limits' in namespace 'std'` — fires even with STL
     reachable, because real `<type_traits>` defines no numeric_limits.
   - Routing radix's RTC arm to `miopen_limits.hpp` is ALSO broken
     (verified live): no signed 64-bit specialization →
     `implicit instantiation of undefined template
     'std::numeric_limits<long long>'`; plus the 6001024024 gate and the
     Linux `-DWORKAROUND_DONT_USE_CUSTOM_LIMITS=1` comgr option route it
     back to real `<limits>` anyway.
   - Minimal correct fix: replace the two uses with literals/builtins, or
     extend miopen_limits with signed long/long long and include it.
   - Also HIP<6.0.25: miopen_cstdint's RTC arm lacks int32_t/uint32_t
     (window gate) → radix typedefs fail even earlier.
2. **MINOR (pathological) — probe asymmetry can double-define std::
   traits when `<utility>` is unreachable but `<type_traits>` is** —
   miopen_freestanding_utility.hpp unconditionally includes the
   freestanding traits. No audited platform triggers it (real STLs ship
   both) but the repo's own shim-dir workaround DOES create that state.
3. **NIT — CMakeLists hunk rewrites all lines for a 3-line semantic
   change** (diff noise).
4. **NIT — unguarded `__has_include`** (clang always has it; non-RTC arms
   never evaluate).

## Attacked with NO breakage

Linux HIP>=7 RTC and non-RTC (probe-true = byte-identical); minimal
containers (probe-false = fix where fatal error was); HIP 5/6 legacy arms
byte-identical; the 6.0.25-6.1.24 window unreachable; `__hip_internal`
never exported to std on 7.14 headers; MSVC coexistence impossible
(`__has_include` tests search-path existence — TU-global); freestanding
initializer_list clean at c++17/c++20 (layout matches clang lowering;
note: no current kernel braced-invokes the ctor); radix host-side/ODR
clean (no host TU includes it; tensor_view host consumers non-RTC →
identical tokens); embed variants covered (INCBIN path uses same list).
