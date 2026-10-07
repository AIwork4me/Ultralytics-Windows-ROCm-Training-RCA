# Phase-3 Gate 80 — Upstream Routing Plan

Date: 2026-10-07. NOTHING HERE HAS BEEN SUBMITTED. This is the routing
map for the human/ChatGPT review to execute (or amend) later.

## 1. rocm-libraries / MIOpen — the source-fix PR

- **Artifact**: `patches/phase3/0001-miopen-hiprtc-selfcontained.patch + 0002-miopen-hiprtc-selfcontained.patch (two-commit series)`
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

## 4b. clr / hiprtc — the contract owner (added per review)

- The component that defines the post-7.0 RTC STL contract (traits moved
  to `__hip_internal`), sets the `x86_64-pc-windows-msvc` triple on
  Windows, and controls include-path policy is clr's hiprtc — absent from
  the original plan. Raise (or fold into the TheRock issue as a
  cross-reference): "hiprtc should ship or auto-discover a freestanding
  std subset in its resource dir" — the single-point fix for MIOpen,
  rocRAND, ComposableKernel and user kernels alike. The likely "by
  design, consumers provide the STL" response is itself the artifact the
  TheRock issue needs (the distribution must then be the provider).

## Ordering recommendation (amended per Gate-83 review: submittable-today items first)

1. **TheRock packaging issue** (submittable TODAY, zero new evidence
   needed; AMD-internal reproduction already exists — their release CI).
2. **ROCm docs prerequisite note** (immediate, trivial; reference the
   TheRock issue so the note has a retirement path).
3. **MIOpen PR** after Linux regression runs complete (gated).
4. **clr/hiprtc lane** (cross-referenced from 1; possibly merged into it).
5. #3956 cross-reference once 3 is public.

## TheRock export-mechanism correction (per Gate-83 review)

The `-I$ROCM_PATH/include` channel fires only when `ROCM_PATH` is set —
unset on stock machines (Gate-50 audit) — and the wheel layout has no
documented `include/` dir. The issue must specify the discovery owner
(wheel post-install env var, torch-loader injection, or preferably
clang/hiprtc resource-dir-based discovery needing no env var), and
propose bundling llvm/libc++ headers (proven viable by TheRock CI
artifacts, PR #3588) rather than MSVC's (licensing/distribution).
