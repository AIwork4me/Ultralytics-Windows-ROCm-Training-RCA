# PHASE 5.2.1 SUMMARY — CI Portability & Reproducible Handoff Closure

Mission: close the remaining CI portability and reproducibility issues
before formal Linux W7900 final A/B validation. STOP boundary: this
mission does NOT run the final A/B; the operational patched leg remains
unbuilt by design.

Integration branch: `linux-w7900/phase5.2.1-ci-closure`
(base: origin/main 4754622 = PR #6 merge; merges the published
phase-5.2 evidence branch 5883db9+c4f9da2 with NO history rewrite).

## Gate C1 — Reproducibility (APPROVED, independent review)

- Integration branch created from current RCA main; published Phase-5.2
  evidence merged as a true merge (history preserved, byte-identical
  commits).
- Exact operative versions of ALL 21→22 runtime/build wrappers published
  under `linux-w7900/phase5.2.1/wrappers/` with sha256 provenance
  (18 IDENTICAL_TO_PUBLISHED, 2 SUPERSEDES_PUBLISHED — the Phase-5.2
  review-driven improvements — 2 workspace-root conveniences first
  published here; +1 measurement wrapper added at Gate C2).
- Clean-checkout verifier `verify_clean_checkout.py`: C1 wrapper hashes,
  C2 documented-script resolution (34 refs), C3 entry points (8),
  C4 Windows phase-5/5.1 artifact preservation (vs origin/main + freeze
  tip 4949076… intact), C5 containment of the published phase-5.2
  commits → VERIFY RESULT: PASS from a fresh clone.
- Windows Phase-5.1 artifacts unchanged: full diff vs main is additions
  under linux-w7900/ only; freeze branch untouched; frozen patches
  re-hash to 14719b8b…/7d40c314…/3eb20ec0….

## Gate C2 — CTest Portability Analysis (APPROVED-WITH-NOTES, independent audit)

- Frozen patch-0003 inspection: manual CTest registration inside
  `if(MIOPEN_USE_HIPRTC)` via `add_test_command`; exit contract
  0/1/2/4 with a mandatory STL-unreachability probe; no skip property
  anywhere in the frozen patch.
- Linux legs: `build_leg_miopen.sh` hardcodes BUILD_TESTING=OFF
  (legA CMakeCache confirmed) → the test is neither built nor discovered
  on validation legs (upstream gating at projects/miopen/CMakeLists.txt:967).
- Isolated test build (worktree at frozen base + 3 patches, tree SHA
  605d0d21… exact; build dir test-BUILD_TESTING-ON; single functional
  delta BUILD_TESTING=ON) → discovery works; three findings:
  - F-C2-1: no-STL positive mode returns exit 4 INCONCLUSIVE on ROCm
    7.14.1 (probe: STL still reachable); unamended CTest renders it
    ***Failed, rc 8. INCONCLUSIVE never counted as PASS.
  - F-C2-2: target does not build on Linux as registered (plain
    `hiprtc` link has no usage requirements; only hiprtc::hiprtc is
    exported). Measured with build-tree-only workarounds; patch untouched.
  - F-C2-3 (discovered at Gate C3): upstream MIOPEN_TEST_GDB defaults
    On on Linux; add_test_command's GDB wrapper collapses every nonzero
    exit into generic failure → SKIP_RETURN_CODE can never match through
    the helper on Linux.
- Exit-code matrix (direct): positive=4, negative=4, with-stl=0 PASS
  (6048-byte code object), ordinary=0 PASS (3824-byte) — controls remain
  executable on Linux.
- Header availability independently re-audited (B06 probe re-run):
  every isolation flag combination leaves
  [type_traits=1, utility=0, limits=1, initializer_list=1] reachable;
  full no-STL isolation NOT reproducible on this host.

## Gate C3 — Minimal CI Fix Proposal (RECOMMEND-WITH-CHANGES → resolved)

- `linux-w7900/phase5.2.1/findings/CI_AMENDMENT_PROPOSAL.md`: two exact
  hunks inside the patch-0003 CMake block (test source untouched):
  1. `if(TARGET hiprtc::hiprtc)` link (capability-aware; fixes F-C2-2;
     no-op on Windows).
  2. Direct `add_test` registration (bypasses the Linux GDB wrapper)
     + `set_tests_properties(... SKIP_RETURN_CODE 4)` (fixes F-C2-1 +
     F-C2-3) + ENVIRONMENT parity; disclosed behavioral deltas
     (skip-list bypass benign for a compile-only test; WORKING_DIRECTORY
     drop harmless — argv-derived absolute paths only).
- Mechanism validated EMPIRICALLY in the build tree (patch untouched):
  direct add_test + SKIP_RETURN_CODE 4 → "***Skipped", "100% tests
  passed, 0 tests failed", rc 0; counterfactuals (wrapper path and
  direct-without-property) → ***Failed rc 8.
- 8 alternatives evaluated and rejected/documented (incl.
  MIOPEN_TEST_GDB=OFF per-leg and mixed registration).
- Requirement matrix satisfied: Windows hard PASS preserved (exit 0/1;
  P5-08 matrix expected unchanged), Linux reports SKIP never PASS,
  ordinary/with-stl still executable, frozen patch untouched by THIS
  mission.
- Maintainer-style independent review: RECOMMEND-WITH-CHANGES; all 10
  findings (4 MINOR disclosure, 6 NIT) applied to the proposal before
  publication.
- Re-freeze checklist hands Windows CodeX an exact path to
  P5.1-CANDIDATE-R2 (DCO placeholder must be resolved; P5.1-R1 history
  must not be mutated).

## Gate C4 — Publication

- Branch `linux-w7900/phase5.2.1-ci-closure` pushed to
  AIwork4me/Ultralytics-Windows-ROCm-Training-RCA with all scripts,
  proposal, real logs and review evidence (see
  evidence/publication.json for the verified remote commit SHA).
- No upstream PR/issue/comment created. Final Linux patched A/B NOT
  executed and NOT claimed.

## Boundary compliance

| Boundary | Status |
|---|---|
| Frozen canonical patch modified | NO (series re-verified intact at every gate) |
| Windows Phase-5.1 artifacts changed | NO |
| Operational patched leg (Leg B) built | NO |
| Final Linux A/B executed/claimed | NO |
| Upstream actions | NONE |
| INCONCLUSIVE counted as PASS | NEVER |
