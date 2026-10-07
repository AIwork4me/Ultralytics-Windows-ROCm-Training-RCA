# Phase-3 Gate 83 — Reviewer C (Windows ROCm packaging specialist)

Date: 2026-10-07. Mandate: "Is the source fix masking a wheel-packaging
defect, or is source self-containment the right ownership boundary?"

## Verdict: SOUND OWNERSHIP (with two misrouted routing elements and one
blocker-grade patch claim)

The mask premise fails: (1) hiprtc's post-7.0 contract ("RTC consumers
include the real STL") is violated by hiprtc's own Windows distribution
(msvc-triple, no stdlib, no discovery config) — self-containment is
defense, not concealment; (2) in-project precedent is decisive
(miopen_limits/miopen_cstdint are the house pattern; #3803/#3147 were the
deviation; rocRAND #8247 fixed the same class in-tree); (3) Gate 79/80
keep the wheel gap alive as a separately-routed item.

## Findings

1. **BLOCKER — the "structurally prevents #7718 coexistence" claim is
   falsifiable by the repo's own published workaround**: the Phase-2
   shim dir (`patches/shim_stl/include/type_traits` via
   `-I$ROCM_PATH/include`) makes `__has_include(<type_traits>)` TRUE
   while `__has_include(<utility>)` FALSE → freestanding utility pulls
   freestanding traits into a TU that already has the shim's traits →
   redefinitions. Regression of a currently-working user configuration.
   Required: unify on one probe or make partial-STL states a LOUD #error,
   and test a partial-STL arm.
2. **MAJOR — moral hazard is real and the plan's ordering amplifies it**
   (TheRock items historically die: #6179 closed unmerged, TheRock#8292
   closed unfixed, #3956 unanswered). Re-order: TheRock issue + docs note
   FIRST (submittable today), MIOpen PR behind its Linux gate.
3. **MAJOR — missing clr/hiprtc lane in the routing plan** (the component
   that owns the STL contract and discovery policy).
4. **MAJOR — TheRock export mechanism inert as written**: `-I
   $ROCM_PATH/include` fires only when ROCM_PATH is set (unset on stock
   machines per the repo's own audit) and the wheel has no documented
   include/ dir. Specify who sets it or use resource-dir discovery;
   bundle llvm/libc++ headers (per TheRock#3588 precedent), not MSVC's.
5. **MAJOR — patch hygiene: whole-file rewrites** (same as A1/D2).
6. **MINOR — rocRAND citation over-reaches** (#8247 suppresses an include;
   it injects nothing into std — same boundary, different mechanism).
7. **MINOR — "cannot regress STL-present environments" is overbroad**
   (false for partial-STL states); scope the claim; note failure mode is
   a loud compile error.
8. **MINOR — freestanding initializer_list is ABI-coupled to clang
   lowering — add `#if !defined(__clang__) #error`.**
9. **MINOR — is_pointer fidelity deviation** (same as A2).
10. **NIT — probe outcome is machine-state-dependent** (cache provenance
    differs across STL states) — one Risk-section sentence.
11. **NIT — docs PR should reference the TheRock issue for retirement of
    the MSVC prerequisite note.**
