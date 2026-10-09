# UPSTREAM ISSUE AND DUPLICATE-FIX AUDIT — Gate P54-07

Mission: `WINDOWS-P54-MIOPEN-UPSTREAM-MERGE-READINESS` · Audited 2026-10-09 via GitHub API (`gh`, account AIwork4me; read-only).

## 1. The authoritative public issue: `ROCm/MIOpen#3956`

| Field | Value |
|---|---|
| Title | "Running BatchNorm2D causes miopenStatusUnknownError" |
| URL | https://github.com/ROCm/MIOpen/issues/3956 |
| State | **OPEN**, 0 comments, label `status: triage` |
| Created | 2026-04-22 by user `mt88875` |
| Reporter config | Radeon RX 9060 XT 16GB (**gfx1200**), Windows 11 25H2, Python 3.12.7, PyTorch **2.9.1+rocm7.2.1**, ROCm **7.2.1** (pip-wheel runtime install, no MSVC/hip-dev) |
| Reproducer | `nn.BatchNorm2d(100)` on `torch.randn(20,100,35,45)` → `miopenStatusUnknownError` |
| Exact failure signature | `MIOpenBatchNormFwdTrainSpatialHIP.cpp` hipRTC compile → `include\miopen_type_traits.hpp:151:10: fatal error: 'type_traits' file not found` … `1 error generated when compiling for gfx1200` |
| Failure chain | `batchnorm_functions.hpp:30 → configuration.hpp:36 → miopen_type_traits.hpp:151` |

**Match assessment**: this is exactly the failure class R2 fixes — a runtime-compiled MIOpen kernel includes host C++ standard headers that a runtime-only Windows ROCm install cannot resolve. The R2 regression test compiles precisely `MIOpenBatchNormFwdTrainSpatial.cpp` under a no-STL include environment and its negative-control asserts this exact `'type_traits' file not found` signature as the *sole* error.

Honest boundaries to state in the PR: the reporter's GPU is gfx1200 (RDNA4); R2 validation hardware is gfx1151 (Windows) and gfx1100 (Linux). The defect is an include-path/availability property of the host environment, not ISA-specific, and the fix contains no arch-conditional code; nevertheless gfx1200 was not directly tested by us.

## 2. Has upstream already fixed it? — No

- Window audit (Gate P54-01): 61 commits base→develop contain **no** change to any of the six R2-modified upstream files, no freestanding-traits work, and `miopen_type_traits.hpp` at develop still has the same unconditional HIP≥7 RTC `#include <type_traits>` arm that produced the field failure.
- No open or merged PR matches `freestanding`/`hiprtc_selfcontained`/`type_traits`-self-containment (0 relevant hits).
- Issue remains open/untriaged-with-no-activity (0 comments since 2026-04-22).

## 3. Adjacent but distinct issues — do NOT claim to fix

| Reference | State | Subject | Relation |
|---|---|---|---|
| `ROCm/rocm-libraries#3956` | OPEN (bug, windows, project: miopen) | "[Issue]: MIOpen tests fails on therock gfx1151 Windows CI Test runners" | **Different issue despite the same number.** TheRock CI failures = GPU-output numerical mismatches & launch failures/timeouts on gfx1151 runners (Jan 2026, ROCm 7.11 prebuilds, 17 comments). NOT the HIPRTC host-header availability failure. ⚠️ **Cross-reference hazard**: R2 commit 3's message contains a bare `#3956`; pushed to rocm-libraries, GitHub would auto-link it to THIS unrelated issue. The PR description must use the full `ROCm/MIOpen#3956` form and note the disambiguation; commit messages are frozen in R2 and are not being rewritten. |
| `ROCm/MIOpen#3803` (PR, merged 2025-06-16) | closed | "All 7.0 hipRTC fixes" | Historical context cited in R2 commit 1 (the 7.0 hipRTC include rework that made kernels reach for real host headers). ⚠️ Commit 1 cites it in **bare** form `(#3803)` — in rocm-libraries that auto-links to the unrelated rocm-libraries PR #3803 ("[hipDNN] Fix backend & data_sdk CMake packaging"). Same hazard class as the bare `#3956`; PR description must disambiguate both. |
| `ROCm/rocm-libraries#3147` (PR, merged 2025-12-18) | closed | "[MIOpen] Update include to use utility if hip version > 7.0" | What R2 commit 1's bare `(#3147)` actually refers to (quoted title matches exactly; touches only `projects/miopen/src/kernels/miopen_utility.hpp`). Resolves **correctly** in the target repo — no hazard. (Distinct from `ROCm/MIOpen#3147`, the cumulative-reduction PR, which is NOT cited by R2.) |
| `ROCm/TheRock#8292` | closed | Windows gfx120X PyTorch release CI: tests fail with `miopenStatusUnknownError` | Corroborating AMD-internal occurrence of the same failure class (cited in R2 commit 1). |
| `ROCm/rocm-libraries#12733` (PR) | OPEN | "resolve HIPRTC bf16 regression (ALMIOPEN-2519)" | Same problem *class* (HIPRTC lacks host dev headers), different root cause (BF16 preamble type availability); file set disjoint from R2's ten files. Non-competing; corroborates motivation. |

## 4. Recommended linkage for the eventual PR

- **Primary**: `Fixes ROCm/MIOpen#3956` (cross-repository full form; the failure signature, kernel, and platform class match exactly). GitHub semantics: closing keywords work cross-repo **only** with the full `OWNER/REPO#N` syntax and only when the PR merges into the target repo's default branch — verified `default_branch: develop` for rocm-libraries, and the PR targets develop, so the merge would auto-close MIOpen#3956 as intended. A bare `#3956` in a commit message closes nothing (no keyword) but links to the wrong issue.
- **Contextual mention only** (not "fixes"): `ROCm/TheRock#8292` (same class, AMD-internal evidence) and open PR `ROCm/rocm-libraries#12733` (parallel HIPRTC robustness work, disjoint files). Corroborating closed same-class precedents worth citing as motivation: rocm-libraries#8247 (rocrand `<utility>` `__HIPCC_RTC__` guard), #10995 (guard HIPRTC includes in ConvDepthwiseFwd3D), #7563 (remove hip includes from RTC kernels).
- **Explicitly out of scope**: `ROCm/rocm-libraries#3956` (TheRock gfx1151 CI numerical failures) — the PR must not imply any relation beyond the number collision; add one disambiguation sentence.
- **Commit-message bare-reference disambiguation note** (frozen R2 messages, not rewritten): bare `#3956` (commit 3) and bare `(#3803)` (commit 1) refer to `ROCm/MIOpen#3956` and `ROCm/MIOpen#3803` respectively, not to the same-numbered rocm-libraries items; bare `(#3147)` (commit 1) correctly refers to rocm-libraries#3147.

## 5. Verdict

No duplicate or superseding upstream fix exists; the target issue is open, unaddressed, and matches the R2 failure class exactly. Linkage prepared as above; nothing in this gate blocks advancement.

**PASS.**
