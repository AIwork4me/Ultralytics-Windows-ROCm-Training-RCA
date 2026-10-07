# Phase-3 Gate 70 — Current Newest Windows ROCm Line Check

Date: 2026-10-07. Method: direct web verification (research subagent,
sources below; VERIFIED = page fetched directly 2026-10-07).

## What is the newest Windows ROCm PyTorch line?

AMD's public versioning has jumped 7.x → 10.x:

| Line | Torch wheel (Windows) | Index |
|---|---|---|
| ROCm 10.1.0 (newest stable) | `torch-2.14.0+rocm10.1.0-cp310…cp314-win_amd64` | `https://stable.repo.amd.com/rocm/whl-next/` |
| ROCm 7.14.x (this machine's line) | newest Windows = `2.12.0+rocm7.14.1` (patch above ours) | `https://repo.amd.com/rocm/whl-multi-arch/` |

- ROCm docs main site is now labeled "AMD ROCm 10.1.0".
- rocm-libraries `develop` is the ROCm 10.x source line.
- Nightly index `https://rocm.nightlies.amd.com/v2/` has per-GPU indices
  incl. gfx1151.
- HIP-SDK Windows installer docs lag (still 7.2.0); they are a separate
  distribution from the pip wheels.

## Is the problematic source gate still present upstream?

**YES — VERIFIED.** `projects/miopen/src/kernels/miopen_type_traits.hpp`
and `miopen_utility.hpp` on `develop` (fetched 2026-10-07) still gate the
no-STL shims behind `HIP_PACKAGE_VERSION_FLAT < 7000000000ULL`; HIP≥7 RTC
unconditionally includes real `<type_traits>`/`<utility>`. Upgrading ROCm
alone is therefore not evidenced to fix the defect, and the patch
developed here remains relevant to the newest line.

## Does standalone HIPRTC still require a host STL on Windows wheels?

**VERIFIED indirectly**: no wheel-side STL bundling has landed. The
wheel-header-parity PR (TheRock#6179, "Add headers present in tarball and
deb but missing in pip wheel") was closed UNMERGED 2026-07-27. TheRock
PR #3588 (2026-02) added llvm C++ headers to TheRock *build artifacts*
(CI), not to pip wheels. AMD's own release-wheel CI still hit
`miopenStatusUnknownError` on Windows gfx120X for torch release/2.12+2.13
(TheRock#8292, opened 2026-09-17, closed with no comments and no linked
fix). No local install of 10.1 was performed (not needed for source-state
analysis; machine isolation preserved).

## Is the defect fixed upstream or in packaging?

**NO.** Accumulated upstream evidence, all still open/unclosed-unfixed:

- MIOpen#3956 (2026-04-22, gfx1200/7.2.1): open, 0 comments, triage
  label, assignee never posted.
- legacy-rocm-build#5941 (2026-02, RX 7900 XTX + others; richest thread;
  same signature incl. gfx1151 nightly 7.12): open; community diagnosis
  "wheel ships runtime binaries only, no SDK headers"; no AMD fix.
- rocm-libraries#7718 (2026-05-23, MSVC ≥14.43 + older MIOpen:
  `std::forward` REDEFINITION — the mirror-direction failure of the same
  shim machinery): closed without visible fix.
- TheRock#8292 (AMD's own CI, 2026-09): closed without linked fix.
- rocRAND fixed ITS copy of the defect class in-tree (rocm-libraries
  PR #8247, merged 2026-07-11: guard `<utility>` with `__HIPCC_RTC__`)
  — an accepted upstream precedent for kernel-source self-containment,
  which MIOpen's own headers did not receive.

## Do Windows wheel docs declare an MSVC prerequisite?

**NO — VERIFIED.** The ai-ecosystem PyTorch install page (Windows tab)
lists Python + AMD driver + ROCm Core SDK only; system-requirements page
mentions no VS/MSVC; pytorch.org mentions VS only for building from
source. The prerequisite remains undeclared (Phase-1 C028 still true).

## Consequences for Phase 3

1. The patch targets `develop` = the SHIPPING 10.x line — maximally
   relevant; no "already fixed" conflict.
2. #7718's mirror failure validates Gate 55's availability-probe design
   (shim must never coexist with real STL) and is cited in
   PATCH_DESIGN.md / FREESTANDING_TRAITS_DESIGN.md.
3. #8247 gives the maintainer-facing precedent: same defect class fixed
   in-project by header guards, accepted upstream.
4. TheRock#8292 gives AMD-internal reproduction weight (their CI).

Sources: rocm.docs.amd.com (latest, ai-ecosystem pytorch install,
install-on-windows + system-requirements), stable.repo.amd.com/rocm/whl-next,
repo.amd.com/rocm/whl-multi-arch, raw.githubusercontent.com/ROCm/rocm-libraries/develop
(both headers), github.com/ROCm/MIOpen/issues/3956 (+ API comments),
github.com/ROCm/legacy-rocm-build/issues/5941,
github.com/ROCm/rocm-libraries/issues/7718, PR #8247,
github.com/ROCm/TheRock issues/PRs #8292/#3588/#6179.
