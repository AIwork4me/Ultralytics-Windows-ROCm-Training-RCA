# Phase 5 Summary — Windows Final Upstream Prep

**Status: `PHASE5_WINDOWS_COMPLETE — DCO_OR_COPYRIGHT_PENDING +
LINUX_FINAL_REVALIDATION_PENDING`** (conclusion JSON:
`findings/phase5/phase5_conclusion.json`; gate table:
`findings/phase5/final_gate.md`).

## What Phase 5 did

1. **Froze and verified the historical chain** — P3 patch hashes
   recomputed from blob bytes (match), Phase-4 canonical commits and
   content verified (8/8 blob-identical reconstruction on the new base).
2. **Assessed current upstream** — develop advanced to `7c58661`
   (7 commits, none in MIOpen); zero drift in the 8 affected files; no
   equivalent fix; ordered series applies clean. Independent review PASS.
3. **Built the Phase-5 candidate** on the frozen develop:
   `135f775e` → `66f66944` → `29846fc4` (branch
   `prepare/miopen-hiprtc-phase5`, worktree `rocm-libraries-phase5-candidate`),
   identity **P5-CANDIDATE-R1** with a fully audited P3→P5 delta
   (dead-macro removal, clang-format 18.1.4 on changed lines, commit-2
   message precision, CI-test commit; adversarially proven
   non-executable).
4. **Integrated the regression test for real** — in-tree
   `test/hiprtc_selfcontained.cpp` + CTest registration under
   `MIOPEN_USE_HIPRTC` with configure-time arch selection; configure /
   build / discovery / execution all PASS on Windows; A/B matrix 13/13
   including adversarial controls; survived a dedicated false-PASS
   attack (all CI-relevant vectors closed; three hardenings applied
   after the attack and independently re-verified).
5. **Built and validated the final DLL** — MIOpen.dll
   `d5974dad0da85b3b9849b5f678fff13b3e678ae14029b98aa0cd87dded9f9a36`;
   load provenance (GetModuleFileNameW + SHA256 in-process), no-STL
   runtime (real isolation + fresh cache), BatchNorm numerics at
   Phase-4 reference accuracy, YOLO26n coco8 training PASS with
   `amp=False` AND genuine default AMP.
6. **Prepared the submission package** — PR draft (with verified
   Background & Motivation, 96 words, independently reviewed),
   maintainer report, DCO/identity audit (email↔account linkage proven
   via GitHub API), Linux targeted-revalidation handoff, machine-
   readable conclusion + SHA256 evidence manifest.
7. **Ran four adversarial final reviews** (maintainer / CI / regression
   attacker / submission auditor) + a focused amendment re-check; every
   evidence-supported BLOCKER/MAJOR resolved (B's Linux-hiprtc-target
   MAJOR fixed and revalidated 13/13).

## What remains (human)

- DCO certification decision; copyright attribution for the four new
  files (then targeted revalidation).
- Linux targeted revalidation (handoff: `findings/phase5/PATCH_HANDOFF.json`).
- Submission-day develop re-check; then human-submitted PR (NOT created
  by this phase).

## Boundaries kept

No upstream PR/issue/comment; no push to ROCm or forks; no internal PR;
historical Phase-3/4 artifacts untouched; machine restored (wheel DLL
`74b4ee03…`, MSVC include present) after every validation.
