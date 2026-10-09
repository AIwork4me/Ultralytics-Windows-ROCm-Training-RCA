# Gate R20 — Independent Subagent Audit (Environment & Historical Source Provenance)

Reviewer: fresh-context general-purpose subagent (agent_d81c797b), read-only,
re-derived every claim with its own commands.

## VERDICT: PASS

All 7 claim groups CONFIRMED, zero falsifications.

Key re-derivations:
- torch 2.12.0+rocm7.14.0; GPU "AMD Radeon(TM) 8060S Graphics"; gcnArchName gfx1151
  (NIT: correct torch attribute is gcnArchName, not gcn_arch_name; value correct).
- wheel MIOpen.dll 74b4ee038803606e6ea4846362a8565fa9e286cb0df18cf80b9e5a7657b78f0a
- wheel hiprtc0714.dll c6159dd12714eed42c1d851e49a425404c1a34ba27cd2a8e721b0fe3db4fd86e
- MSVC 14.44.35207 sole toolset under C:\BuildTools\VC\Tools\MSVC
- cmake 4.4.4 / ninja 1.13.2.git.kitware.jobserver-pipe-1 at phase3_buildtools paths
- R1 branch = 494907699f3b57095663f0a70b42278001a8efb7 (subject "phase5.1: final candidate freeze (P5.1-CANDIDATE-R1)"); R1 canonical patches re-hashed from git blob bytes: 14719b8b… / 7d40c314… / 3eb20ec0… — all match mission-frozen identities.
- origin/main = 73e51c440c53c1fb12594fe959934f494ab86235 (PR #7 merge, Linux 5.2.1 findings present).
- rocm-libraries: R1 worktree HEAD e7ff6d75, tree 605d0d21, clean; new R2 worktree
  rocm-libraries-phase5.1-r2-candidate on prepare/miopen-hiprtc-phase5.1-r2 at base
  7c586614, clean; R1 commit parent chain d4003de1 → 3b18a065 → e7ff6d75 → parent 7c586614 verified.
- R1 manifest findings/phase5_1/FINAL_HANDOFF.json exists at 4949076 with candidate_id P5.1-CANDIDATE-R1.

NITs (informational): (a) attribute-name nit above; (b) RCA working tree (on the new
R2 branch) contains untracked evidence/phase5_1_r2/ — in-progress R2 scaffolding,
outside the R1-branch cleanliness claim.

Full command list preserved in the review transcript; raw environment capture at
evidence/phase5_1_r2/environment/r20_environment_audit.txt.
