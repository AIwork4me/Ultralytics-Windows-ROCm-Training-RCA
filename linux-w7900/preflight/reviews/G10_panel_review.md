# G10 Final Independent Readiness Panel — Consolidated Record

Date: 2026-10-08 (UTC) | Mission: W7900-LINUX-PREP-R1

Three fresh independent subagent reviewers (no shared context with the
primary agent or with each other).

## REVIEWER A — Linux ROCm Environment: CONDITIONAL PASS

- All 8 scope items verified live (gfx1100 genuine, driver access, 7.2.1
  untouched, 7.14.1 venv functional, HIPRTC resolution, CMake cache clean,
  isolation, system safety).
- MAJOR-1: G01 isolation_hardening claim overstated (env -i still mapped
  libhsa-amd-aqlprofile64 from system; 5 lazy sonames fell back to 7.2.1
  without LD_LIBRARY_PATH).
  RESOLVED same-session: all stray sonames symlinked into torch/lib
  (12 additional); clean-env ldd now resolves ZERO /opt/rocm libraries;
  G01 evidence corrected (correction_G10_reviewA); run-protocol guard
  added to ENVIRONMENT_REPRODUCIBILITY.md and FINAL_HANDOFF_CONSUMER.md;
  sourcing env_rocm7141.sh remains the mandatory operative rule.
- MINORs: no RPATH on built binaries (isolation concentrated in wrapper —
  accepted, documented); pipefail+head advisory (documented).

## REVIEWER B — MIOpen Build & Runtime: PASS

- Baseline sha256/cache/version verified; MIOpenDriver 3.6.2 correctly
  bound; harness zero link-time ROCm deps.
- CRITICAL repeatability check: fresh-label kthvalue rerun PASS 3/3;
  **dumps byte-identical 15/15 (cmp)** vs original run; RTC kernel_hash
  values reproduced exactly (ebb749a6…, 050ca32f…).
- A/B scripts: identical flags, B dirs empty, leg-b interlocks intact;
  own adversarial retests of the G08 hardening all REJECTED correctly.
- No blockers; no required actions.

## REVIEWER C — Final Submission Evidence: CONDITIONAL PASS

- RCA harness diff = single banner line; manifest consumer raw-bytes
  discipline verified; apply interlock verified; ROGUE-patch negative test
  correctly FAIL.
- No premature patched claims anywhere; all 14 evidence JSONs valid+gated;
  reviews G00–G08 complete with no unresolved BLOCKER/MAJOR.
- M-1 (MAJOR): leg-A rebuild at frozen SHA was required-but-not-executable
  (runbook gap). RESOLVED: prepare_validation_legs.sh leg-a [frozen_sha]
  now worktree-reconstructs leg-A source at the frozen SHA (mirroring
  leg-b); RCA_REPO_ROOT acquisition documented.
- m-1: cross-directory basename hole in unlisted-file check.
  RESOLVED: per-directory declared sets; attack re-tested -> FAIL.
- m-2: G09 review artifact missing. RESOLVED: dedicated G09 subagent run
  (see reviews/G09_subagent_review.md; verdict PASS after two evidence
  fixes) + this consolidated record.
- m-3: G07_library_sha256.json path now referenced in G07 readiness JSON.
- m-4: timestamps added to payload evidence files.

## PANEL CONSENSUS

All justified BLOCKER/MAJOR findings resolved during preparation with
recorded proof. Panel verdicts: A CONDITIONAL PASS (resolved), B PASS,
C CONDITIONAL PASS (resolved). **No unresolved readiness blockers.**

**OFFICE_W7900_ENV_READY** (subject to the known transient: rocm-libraries
worktree backfill still completing through the unstable egress proxy —
mitigated by the tarball source-of-record + verification path, and by
clone/fetch retry tooling shipped in scripts/).
