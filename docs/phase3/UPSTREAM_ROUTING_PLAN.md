# Phase-3 Gate 80 — Upstream Routing Plan

Date: 2026-10-07. NOTHING HERE HAS BEEN SUBMITTED. This is the routing
map for the human/ChatGPT review to execute (or amend) later.

## 1. rocm-libraries / MIOpen — the source-fix PR

- **Artifact**: `patches/phase3/miopen_hiprtc_freestanding_v2.patch`
  (+ PR text draft in `docs/phase3/PR_DRAFT.md`).
- **Content**: availability-probed freestanding `<type_traits>`/`<utility>`
  selection in `miopen_type_traits.hpp`/`miopen_utility.hpp` (HIP<7 legacy
  arms untouched), `radix.hpp` RTC include routing, `tensor_view.hpp`
  initializer_list probe, three new freestanding headers, embed-list
  registration in `src/CMakeLists.txt`.
- **Pre-submission blockers (owner: submitter)**: Linux HIP≥7 regression
  runs (Gates 72-74 blocked here); optionally land the canary suite as CI.
- **References to cite**: MIOpen#3956 (identical failure), #7718 (mirror
  failure proving shim/STL coexistence must be prevented — validates the
  probe design), rocRAND PR #8247 (in-project self-containment precedent).

## 2. TheRock / Windows wheel packaging — separate issue

- **Problem statement**: AMD Windows pip wheels ship an
  `x86_64-pc-windows-msvc` clang + hiprtc with no C++ stdlib, no
  include-path configuration, and no documented runtime STL provider;
  every wheel component relying on hiprtc real-std includes fails on
  stock installs (this RCA's MIOpen evidence + AMD's own TheRock#8292 CI
  failure on release/2.12+2.13 gfx120X).
- **Proposals to raise**: bundle a freestanding std-subset (or full STL)
  into the wheel and export via the already-honored `-I$ROCM_PATH/include`
  channel (Phase-2 poison-header proof), OR document MSVC Build Tools as
  a prerequisite (interim docs fix).
- **Prior art to cite**: TheRock PR #3588 (added llvm C++ headers to CI
  artifacts for the same signature), TheRock PR #6179 (wheel header
  parity — closed unmerged; the gap persists), legacy-rocm-build#5941
  (user-visible thread).

## 3. ROCm documentation — prerequisite note (interim)

- Until either fix lands, the Windows PyTorch wheel install docs should
  state that MIOpen runtime-compiled operators (spatial BatchNorm without
  fused inference, etc.) require MSVC C++ Build Tools (or an STL
  provider) on the machine. One-paragraph docs PR, lowest risk, highest
  immediate user value.

## 4. MIOpen#3956 — cross-reference (later, with human approval)

- After the source PR exists, a comment linking the PR + this RCA repo
  would close the loop for the reporter (issue open since 2026-04-22,
  zero AMD response). REQUIRES explicit human approval per the brief.

## Ordering recommendation

1. ROCm docs prerequisite note (immediate, trivial).
2. MIOpen PR after Linux regression runs complete.
3. TheRock packaging issue (parallel to 2; independent owner).
4. #3956 cross-reference once 2 is public.
