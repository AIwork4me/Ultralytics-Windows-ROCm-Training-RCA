# PHASE 6 — Linux / cross-platform safety review (Round-3, d4b574ac)

Windows gfx1151 validation cannot prove Linux behavior; this is the code-level
review plus the CI-evidence categorization. Local Linux runs: NOT AVAILABLE
(no Linux GPU runner on this machine) — disclosed, per mission.

## Code-level analysis (diff d4b574ac vs f0f330c4)

| Concern | Finding |
|---|---|
| Normal host-STL compilation | Fallback still gated by `#if defined(MIOPEN_HIP_RUNTIME_COMPILE) && !__has_include(<X>)`; offline paths include the same standard headers (`<type_traits>` / `<utility>` / `<initializer_list>`); the new initializer-list wrapper has no develop counterpart. All offline kernel builds (Linux + Windows) take the `#else` path. Round-3 touched only fallback-branch internals, comments, whitespace. |
| HIPRTC with compiler-injected STL (typical Linux comgr) | `__has_include(<type_traits>)` true → real STL include; fallback inactive. Selection conditions unchanged from Round-2. |
| HIPRTC without host STL (Windows wheels) | Fallback active; validated on gfx1151 this round (B gtest PASS, cache label `3.6.2.d4b574ac`, 5 fresh compiles; kthvalue 27/27 fresh cache; BatchNorm A/B printed error summaries identical; YOLO per F log). |
| Removed partial-STL `#error` diagnostics | Linux standard libraries ship the three headers together; a partial mix essentially cannot occur with a real toolchain. An arbitrary partial mix now relies on natural compiler diagnostics; consistency and a particular error are not guaranteed. Diagnostic-only change, explicitly requested (comment r4286709599). |
| `GTEST_SKIP` semantics | Regression test byte-identical (frozen this round; naming hook PASS). Linux comgr STL-injection → skip leg unchanged from Round-2 behavior already reviewed by maintainer and exercised by Linux CI. |
| Duplicate STL definitions | Real headers are selected independently by `__has_include`. Complete standard libraries are the normal supported environment; arbitrary partial-header consistency is no longer enforced after the requested guard removal. No failing supported configuration was observed; include graph is unchanged from Round-2. |
| Clang C++ template regressions | Round-3 reverts restore develop's exact template text (typedefs, conditional fwd-decl + partial specializations, flat `is_pointer_helper`) — text that compiled in production for years (HIP 6.x branch, clang). New code (aliases, real `enable_if`, `is_trivially_copyable`) is unchanged from Round-2, which passed clang-tidy + Linux CI. Declaration-before-use verified after the `integral_constant` move (dependents: `is_same`, `is_pointer_helper`, `is_trivially_copyable` — all later). |
| New header dependencies | None (comment/whitespace/text-form changes only; include graph identical). |

## CI evidence categories

- Round-2 head f0f330c4 (superset of Round-3's code minus the cleanups): Linux
  Component CI PASS, TheRock CI PASS, TheRock Multi-Arch ASAN PASS, clang-tidy
  PASS (runs 2026-10-14, see PHASE0_BASELINE.md).
- Round-3 head d4b574ac: local Windows functional suite PASS (this mission);
  seven current-head GitHub workflows are ACTION_REQUIRED as of the 2026-10-17 closure
  audit; execution is awaiting maintainer approval. No current-head Linux PASS is claimed.
- gfx942 "GPU Hang" (run 38596620066): separate classification in
  GFX942_CI_RCA.md — not a Windows-vs-Linux equivalence claim.

**Gate B+D: PASS (review)** — no cross-platform assumption in the Round-3
change; Linux residual risk is limited to CI re-run on push.
