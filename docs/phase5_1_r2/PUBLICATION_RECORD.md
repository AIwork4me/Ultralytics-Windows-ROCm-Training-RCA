# PUBLICATION RECORD — P5.1-CANDIDATE-R2 evidence branch

Branch: phase5.1/windows-r2-ci-portability-freeze
Repository: https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA

## Verified frozen evidence snapshot

Remote commit `cd9c36c52a7702eef4a2b4ba899a4e35dfba8b1a`
(the complete candidate-freeze evidence; this record and any later
housekeeping commits sit ON TOP of it and do not modify it).

Machine verification performed 2026-10-09 after push:
- `git rev-parse origin/<branch>` == cd9c36c52a7702eef4a2b4ba899a4e35dfba8b1a (REMOTE-HEAD-MATCH)
- findings/phase5_1_r2/FINAL_HANDOFF.json present at the remote ref
- patches/phase5_1_r2/canonical/{0001,0002,0003}*.patch present; remote
  git-blob SHA256 = 816946b4… / 46044d8c… / df7c3c3a… (byte-exact)
- Remote series hash (sha256_file_concat_v1) =
  48308f6dccfd80f099a458ad5033f815d95f86d2ab54dba1a0344c976b5a3f02
- Verifiers against the published ref: verify_patch_identity 25/25,
  verify_final_handoff 39/39.

## Linux validator entry point

Pin `cd9c36c52a7702eef4a2b4ba899a4e35dfba8b1a` (or the branch tip), then
follow docs/phase5_1_r2/LINUX_FINAL_VALIDATION_HANDOFF.md §0.

## Boundaries respected

No upstream (ROCm/AMD) PR, issue, or comment. No internal PR. R1 branch
untouched. The candidate worktree branch (prepare/miopen-hiprtc-phase5.1-r2
in the local rocm-libraries clone) is local-only — the canonical upstream
artifact is the patch series, not a pushed branch.
