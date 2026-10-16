# PHASE 6 — Linux / cross-platform safety review (Round-3, d4b574ac)

Windows gfx1151 validation cannot prove Linux behavior; this is the code-level
review plus the CI-evidence categorization. Local Linux runs: NOT AVAILABLE
(no Linux GPU runner on this machine) — disclosed, per mission.

## Code-level analysis (diff d4b574ac vs f0f330c4)

| Concern | Finding |
|---|---|
| Normal host-STL compilation | Fallback still gated by `#if defined(MIOPEN_HIP_RUNTIME_COMPILE) && !__has_include(<X>)`; `#else` branches byte-identical to develop (`#include <type_traits>` / `<utility>` / `<initializer_list>`). All offline kernel builds (Linux + Windows) take the `#else` path. Round-3 touched only fallback-branch internals, comments, whitespace. |
| HIPRTC with compiler-injected STL (typical Linux comgr) | `__has_include(<type_traits>)` true → real STL include; fallback inactive. Selection conditions unchanged from Round-2. |
| HIPRTC without host STL (Windows wheels) | Fallback active; validated on gfx1151 this round (B gtest PASS, cache label `3.6.2.d4b574ac`, 5 fresh compiles; kthvalue 27/27 fresh cache; BatchNorm A/B numerically identical; YOLO per F log). |
| Removed partial-STL `#error` diagnostics | Linux standard libraries ship the three headers together; a partial mix essentially cannot occur with a real toolchain. If it ever did, the TU now fails with the compiler's natural missing-include error instead of a custom `#error`. Diagnostic-only change, explicitly requested (comment r4286709599). |
| `GTEST_SKIP` semantics | Regression test byte-identical (frozen this round; naming hook PASS). Linux comgr STL-injection → skip leg unchanged from Round-2 behavior already reviewed by maintainer and exercised by Linux CI. |
| Duplicate STL definitions | Impossible by construction: each fallback guarded by its own `!__has_include`; no new headers, no new cross-includes (utility→type_traits, tensor_view→initializer_list, radix→{cstdint,type_traits} — identical graph to Round-2). |
| Clang C++ template regressions | Round-3 reverts restore develop's exact template text (typedefs, conditional fwd-decl + partial specializations, flat `is_pointer_helper`) — text that compiled in production for years (HIP 6.x branch, clang). New code (aliases, real `enable_if`, `is_trivially_copyable`) is unchanged from Round-2, which passed clang-tidy + Linux CI. Declaration-before-use verified after the `integral_constant` move (dependents: `is_same`, `is_pointer_helper`, `is_trivially_copyable` — all later). |
| New header dependencies | None (comment/whitespace/text-form changes only; include graph identical). |

## CI evidence categories

- Round-2 head f0f330c4 (superset of Round-3's code minus the cleanups): Linux
  Component CI PASS, TheRock CI PASS, TheRock Multi-Arch ASAN PASS, clang-tidy
  PASS (runs 2026-10-14, see PHASE0_BASELINE.md).
- Round-3 head d4b574ac: local Windows functional suite PASS (this mission);
  Linux CI NOT YET RUN — will trigger on push (Phase 9); to be reported after
  the push, not claimed in advance.
- gfx942 "GPU Hang" (run 38596620066): separate classification in
  GFX942_CI_RCA.md — not a Windows-vs-Linux equivalence claim.

**Gate B+D: PASS (review)** — no cross-platform assumption in the Round-3
change; Linux residual risk is limited to CI re-run on push.
