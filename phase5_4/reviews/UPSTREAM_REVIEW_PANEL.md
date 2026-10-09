# GATE P54-11 — FOUR-REVIEWER UPSTREAM PANEL (final)

Mission: `WINDOWS-P54-MIOPEN-UPSTREAM-MERGE-READINESS` · 2026-10-09 · Four FRESH independent subagents, each instructed to challenge prior gates rather than rubber-stamp. All reviewers ran their own commands; every hash and verdict below was independently recomputed by at least one reviewer.

| Reviewer | Persona | Verdict | Blockers | Majors | Minors | GO/NO-GO |
|---|---|---|---|---|---|---|
| A | MIOpen C++ Maintainer | **PASS** | 0 | 0 | 3 | **GO** |
| B | MIOpen CI Maintainer (CMake/CTest) | **PASS** | 0 | 0 | 3 | **GO** |
| C | GPU Runtime / Numerical Engineer | **GO** | 0 | 1 (administrative: evidence not yet committed) | 4 | **GO** (conditional on commit) |
| D | Upstream Submission / Supply-Chain Auditor | **PASS WITH CONDITIONS** | 0 | 1 (time-based: develop drift) | 3 | **GO** (conditional on submission-day refresh) |

## Reviewer A — C++ (PASS/GO)

Independent re-derivation with four new first-hand experiments: regression test re-executed in 5 modes (ordinary/positive/negative-on-patched/with-stl/bad-dir — contract 0/1/2 reconfirmed); a 25-assert differential trait torture compiled through hipRTC on both legs (freestanding vs real STL — both pass, stricter than the file's own self-tests); 12/12 preprocessor-quadrant token-equality between base and tip; partial-STL cross-`#error`s fire both directions. New findings strengthening the case: a full `src/kernels` host-STL include census (the four patched chokepoints + upstream's own shims are the *complete* RTC-relevant STL surface) and proof that `MIOPEN_HIP_RUNTIME_COMPILE` is emitted only from the AMD hipRTC path (`src/comgr.cpp:805`), confining all clang-only constructs to clang by construction. `SOURCE_FIX_DELTA_FROM_R2=NONE` confirmed (10/10 blobs). Minors (all PR-text): radix substitution is unconditional (only the include switch is RTC-gated); "define fidelity" overclaims (inert layout defines; per-instance value-defines covered by `default_configurations.hpp`); add the new-file-vs-inline rationale sentence. **All three fixed in `UPSTREAM_PR_DRAFT_FINAL.md` this session.** Experiments preserved in `phase5_4/reviewerA_torture/`.

## Reviewer B — CI/CTest (PASS/GO)

Re-executed registration/bare-env/exit-code/property checks and added a counter-check: launching the test exe directly with minimal PATH fails with STATUS_DLL_NOT_FOUND — proving the CTest `ENVIRONMENT` PATH prepend is load-bearing. Verified `CTestTestfile.cmake` properties and the `hiprtc::hiprtc` link branch in `build.ninja`. New finding: ambient `CPATH` on CI images silently converts the no-STL verdict to Skipped-green (capability-aware, never false — but a coverage-loss vector) → PR sentence + pipeline assertion recommendation. Minors: commit the two ad-hoc check commands (done: `scripts/bare_env_and_restricted_leg_checks.py`, replayed OK), single-host PATH contract note (done), `echo skipped` warning parity with upstream helper (nit). No source change recommended.

## Reviewer C — Runtime/Numerical (GO)

Independently re-hashed the DLL (`44d43887…`), the wheel (`74b4ee03…` now), and all patch series; confirmed BN numerics **bit-identical** to the frozen R2 measurement from a *different* DLL build (deterministic kernels, genuine fresh re-measurement); verified no-STL isolation semantics, 13-cell matrix unpatched-tree identities (every "unpatched" cell provably used the pristine develop worktree), AMP honesty (both raw behaviors reported, no upgrade), and Linux R2-tree scoping. Major 1: `phase5_4/` not yet committed/pushed — administrative, resolved by Gate P54-13. Minors fixed this session: `env_scrubbed` under-report correction, YOLO stderr-noise disclosure, full sha restoration. Recommended (deferred, non-blocking): assert tree identity in `run_ci_matrix.py::expect()`.

## Reviewer D — Supply chain (PASS WITH CONDITIONS/GO)

Every identity recomputed from primary artifacts: commit chain, patch hashes (both series), 10/10 blob manifest, R2 remote immutability (reflog fast-forward proof), replay commits local-only, copyright/DCO/no-unauthorized-action (GitHub API sweeps returned zero). **M-1 (the one substantive finding): upstream `develop` moved past the candidate base minutes after freeze** (observed `5af159d6`, later `aa966601`; 3 commits, fast-forward). Handled per mission rule: new SHA recorded, drift audited (**zero `projects/miopen` changes; ten-file blob audit identical**), candidate base **not** silently changed, submission-day refresh procedure mandated (`SUBMISSION_DAY_CHECKLIST §1`; PR draft amended with timestamped claim). Minors fixed this session: PR draft now cites both patch-series hash sets; pre-filled attestation removed from CONTRIBUTION_COMPLIANCE.md; `no-push` guardrail set on the replay worktree's origin.

## Resolution ledger (all justified technical findings)

| Finding | Class | Resolution |
|---|---|---|
| D-M1 develop drift | MAJOR (time) | Audited (no miopen impact), recorded everywhere, base unchanged, checklist §1 mandatory refresh — **resolved procedurally** |
| C-M1 evidence unpublished | MAJOR (admin) | Gate P54-13 commit+push+remote-verify |
| A-m1/2/3, D-m1, B-m2 | MINOR | PR-draft text edits — **applied** |
| B-m1 ad-hoc commands | MINOR | `bare_env_and_restricted_leg_checks.py` committed + replayed OK — **applied** |
| C-m1/2, C-n3 | MINOR | JSON corrections/annotations — **applied** |
| B-m3 single-host note, D-m3 attestation policy, D-n1/n2 guardrails | MINOR/NIT | **applied** |
| C-m3 expect() identity assert | MINOR | **deferred** (documented follow-up; changing the validated matrix script now would invalidate the 13/13 evidence identity) |
| All NITS (A 1–6, B 1–5, C 1–2, D 1–2) | NIT | maintainer-Q&A material; recorded in panel outputs |

**Panel conclusion: 0 technical blockers, 0 unresolved majors after resolutions; unanimous GO.** Governance items (upstream PR authorization, DCO-if-desired, submission-day refresh) remain explicitly pending human action.
