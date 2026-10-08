# Maintainer Report — Final (Gate P5-16)

Candidate **P5-CANDIDATE-R1**: 3 commits over ROCm/rocm-libraries develop
`7c58661` (frozen 2026-10-08), prepared on Windows by the contributor.
This report summarizes the engineering case for review; the PR text is in
`PR_DRAFT_FINAL.md`. Nothing here has been submitted to any AMD
repository.

## The fix in one paragraph

Runtime-compiled MIOpen kernels must not require a host C++ standard
library that HIPRTC does not guarantee. The series (1) makes
`miopen_type_traits.hpp` / `miopen_utility.hpp` prefer the real
`<type_traits>` / `<utility>` via `__has_include` and fall back to new
self-tested freestanding headers only when no stdlib resolves, (2) makes
the remaining kernel std includes (`<limits>` in radix.hpp,
`<initializer_list>` in tensor_view.hpp) self-contained the same way,
and (3) adds a compile-only CTest regression that compiles the real
`MIOpenBatchNormFwdTrainSpatial.cpp` through hiprtc with the host STL
unreachable.

## Why now

Ultralytics' AMD GPU support announcement (v8.4.171, Oct 1 2026) made
Windows ROCm training a mainstream path; the first real training run on
Radeon 8060S (gfx1151, tested with Ultralytics 8.4.174) hit this defect
immediately. The defect predates the announcement (MIOpen#3956, since
HIP 7.0 — see #3803 / #3147 history in the PR draft).

## Reproducible validation summary (all evidence logged in this repo)

Windows — Phase-5 candidate, fresh runs (gfx1151, ROCm 7.14.0,
PyTorch 2.12.0+rocm7.14.0):

| Check | Result | Evidence |
|---|---|---|
| Upstream applicability (develop `7c58661`) | zero drift in all 8 affected files; no equivalent fix; ordered series applies clean | `docs/phase5/UPSTREAM_BASE_ASSESSMENT.md`, review PASS |
| Candidate = validated content + audited delta | 8/8 blob-identical before hygiene edits; then only dead-macro removal + clang-format 18.1.4 + message fix | `P3_TO_P5_DELTA.md`, adversarial review: nothing executable changed |
| CMake configure / target build / CTest discovery / CTest run (BUILD_TESTING=ON, in-tree) | PASS ×4 | `evidence/phase5/ci/` |
| CI A/B matrix (incl. 5 adversarial controls) | 13/13 PASS | `ci_matrix_phase5.json` |
| Independent false-PASS attack on the test | see `findings/phase5/reviews/P508_false_pass_attack.md` | — |
| MIOpen.dll source build (RelWithDebInfo) | PASS — SHA256 `d5974dad0da85b3b9849b5f678fff13b3e678ae14029b98aa0cd87dded9f9a36` | `evidence/phase5/build/` |
| Loaded-DLL provenance (GetModuleFileNameW + SHA256 in workload process) | PASS — exact Phase-5 DLL | `evidence/phase5/runtime/dll_provenance.json` |
| No-STL runtime (MSVC include renamed, fresh profile/cache ⇒ real RTC recompile; BN train/backward/running stats) | PASS | `runtime/nostl_validation.json` |
| BatchNorm numerics (fp32 GPU vs fp64 CPU; tolerances fixed pre-run) | PASS — output max_abs 6.71e-07 (Phase-4 reference 6.85e-07); grads 3.2e-12 / 2.4e-08 / 1.9e-09; running stats ~1e-10; all finite, no NaN/Inf | `runtime/runtime_validation.json` |
| YOLO26n coco8 1-epoch, amp=False | PASS — epoch + val completed, best.pt/last.pt, exit 0 | `yolo/yolo_train.json` |
| YOLO26n coco8 1-epoch, default AMP | PASS — genuine AMP ("AMP: checks passed", `amp=True`), epoch + val completed, weights saved | same |

Linux:

| Check | Status |
|---|---|
| P3 content: source-built unpatched PASS / patched PASS; numerics bit-identical; kthvalue PASS→PASS | HISTORICAL VALIDATION (independent validator branch) |
| Phase-5 candidate on Linux | PENDING NEW VALIDATION — targeted handoff: `LINUX_FINAL_VALIDATION_HANDOFF.md` + `findings/phase5/PATCH_HANDOFF.json` |

## Known deltas vs the historically validated bytes

1. Base moved `b68f894` → `7c58661` (upstream's own progress; affected
   files untouched; BN kernels carry an upstream `use_amdgcn`→
   `use_gfx9_dpp` rename — our numerics above already validate it).
2. Dead `MIOPEN_FREESTANDING_TRAITS_ACTIVE` macro removed (zero
   references anywhere).
3. clang-format 18.1.4 applied to changed lines (repo-pinned pre-commit
   version; the 7 kernel headers are now format-clean).
4. Commit-2 message corrected (builtin-limits replacement is
   unconditional, not runtime-path-only).
5. CI test added (commit 3).

## Outstanding before submission (human actions)

1. DCO sign-off (commits are unsigned with an explicit pending marker;
   MIOpen's contributing guide does not mandate DCO, but the monorepo PR
   bot may — exact finalize command in `AUTHORSHIP_DCO_AUDIT.md`).
2. Copyright attribution for the 3 new MIT headers
   (`COPYRIGHT_ATTRIBUTION_PENDING`; placeholders retained; after
   fill-in, rerun the targeted validation — comment-only byte change).
3. Linux targeted revalidation per the handoff.
4. Re-check develop applicability on submission day (Gate P5-02 method).

## Upstream CI follow-ups (post-merge)

- Cross-architecture compile-only legs (gfx94x/gfx110x/gfx120x, one
  HIP 10.x line) — the test accepts `--arch`/`MIOPEN_TEST_HIPRTC_ARCH`.
- `audit_rtc_std_dependencies.py` as a CI ratchet (Phase-3 proposal).

## Status of upstream actions

```text
UPSTREAM PR CREATED: NO
UPSTREAM ISSUE CREATED: NO
UPSTREAM COMMENT POSTED: NO
INTERNAL PR CREATED: NO
```
