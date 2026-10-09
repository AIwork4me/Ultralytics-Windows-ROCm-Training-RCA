# PHASE 5.1 R2 — CI PORTABILITY AMENDMENT → WINDOWS REVALIDATION → RE-FREEZE

Mission WINDOWS-P51-R2-UPSTREAM-CLOSURE — completed 2026-10-09 on
Windows 11 / Ryzen AI MAX+ 395 / Radeon 8060S (gfx1151).

## Outcome

**P5.1-CANDIDATE-R2** frozen: `TECHNICALLY_VERIFIED_PROVISIONAL_FREEZE`
(manifest `findings/phase5_1_r2/FINAL_HANDOFF.json`). Verdict line:
**R2_WINDOWS_FROZEN_WITH_HUMAN_COMPLIANCE_PENDING** (Linux validation and
human submission authorization outstanding; upstream PR NOT created).

| Identity | Value |
|---|---|
| Upstream base (frozen) | `7c5866144ac4b879be442563e2b49fa1c142ea36` |
| R2 commits | `01a77dab` → `8188b803` → `d758aed7` |
| R2 source tree | `060087061488a83a931f1d8d1ad2c0eb6c231eac` |
| Series SHA256 (concat v1) | `4a703d69cc3e111408fad593761a3f017619ced4cf007f0f565ca98472c91bcf` |
| Patch SHA256 0001/0002/0003 | `816946b4…` / `46044d8c…` / `db16ee9e…` |
| R2 MIOpen.dll (rebuilt+proven) | `eb0a1bf0d31cac5ae7597df423f3d6cb26f433df9c20110ae1d51fddd6ed0bfd` |
| R1 (superseded, immutable) | branch `phase5.1/windows-final-candidate-freeze` @ `4949076`, series `797a69b5…`, tree `605d0d21…` |

## What changed vs R1 (one file, +84/−16)

`projects/miopen/test/CMakeLists.txt` test registration block only — all
production kernel headers and the test C++ source are byte-identical to R1
(per-file git-blob verified):

1. **F-C2-2** link: platform split → `if(TARGET hiprtc::hiprtc)` capability
   split (Linux hiprtc package exports only the namespaced imported target).
2. **F-C2-3** registration: direct `add_test` instead of `add_test_command`
   whose Linux `MIOPEN_TEST_GDB` cmake -P wrapper collapses every nonzero
   exit (incl. INCONCLUSIVE 4) into a generic failure.
3. **F-C2-1** verdicts: `SKIP_RETURN_CODE 4` — honest INCONCLUSIVE renders
   as CTest Skipped/Not-Run on hosts that cannot reproduce no-STL
   isolation; genuine verdicts stay hard (0 PASS / 1 FAIL / 2 FAIL).
4. **Policy parity**: the direct registration replicates add_test_command's
   exact `SKIP_TESTS` / `SKIP_ALL_EXCEPT_TESTS` guard (restricted legs —
   MIOPEN_NO_GPU, INT8, BF16 — keep disabling the test; empirically proven
   on a BF16 leg) and its `MIOPEN_USER_DB_PATH` ENVIRONMENT.
5. **F-C2-4** (discovered during this mission's revalidation, user-directed):
   Windows DLL loader — a bare ctest run could not START the test
   (`0xC0000135 STATUS_DLL_NOT_FOUND`: hiprtc DLL lives in `<prefix>/bin`,
   import lib in `<prefix>/lib`). Fixed test-scoped: runtime directory
   derived from the imported target's location metadata and prepended to
   PATH in the test's ENVIRONMENT (escaped so the value stays one entry).
   No machine-wide PATH change, no DLL copies. Latent in R1 too (evidence
   scripts masked it by pre-setting PATH). Full RCA:
   `findings/phase5_1_r2/F_C2_4_DLL_LOADER_RCA.md`.

Commit messages: DCO placeholder lines REMOVED from all three (no
Signed-off-by added — certification not authorized; upstream policy has no
DCO requirement). Commit 3 subject updated to "…portable…". Production
source delta R1→R2: zero.

## Windows validation (all PASS on final HEAD d758aed7)

Fresh `phase5_1_r2_build/ci_test` (BUILD_TESTING=ON): configure, build,
discovery, execution PASS — genuine no-STL PASS (not skipped). Clean-env
ctest (no ambient ROCm PATH) PASS post-F-C2-4 fix; loaded hiprtc0714.dll
proven in-process (psutil) = `c6159dd1…`. 13/13 adversarial matrix.
Exit-code fixture 0→PASS / 1→FAIL / 2→FAIL / 4→SKIP. BF16 restricted-leg
parity. MIOpen.dll rebuilt (`eb0a1bf0…`), loaded-path + in-process SHA
proven, no-STL fresh-profile BatchNorm PASS, numerics within tolerances
(y 6.7e-7-class), YOLO26n coco8 amp=False PASS and default-AMP PASS with
GENUINE amp=True this run (R1's environment-dependent AMP-check failure no
longer present — control evidence in R1 showed it affected the pristine
wheel identically). Wheel DLL restored and verified `74b4ee03…`.

## Independent audits (fresh subagents, every gate)

R20 provenance PASS · R21 defect analysis PASS · R22 line-by-line source
PASS · R23 maintainer A PASS + false-pass auditor B PASS · R24 commit
archaeology PASS · R25 adversarial matrix audit PASS · F-C2-4 A (DLL
provenance) PASS + B (portability/false-pass) PASS (MINOR-1 hardening
applied: full escaped PATH tail). R33 four-way merge-readiness review:
see findings/phase5_1_r2/reviews. No unresolved BLOCKER or MAJOR.

## Compliance

Copyright (c) 2026 AIwork4me preserved in 4/4 new files; MIT text intact.
DCO: unsigned by design (policy inspected at frozen base — no requirement;
user has NOT authorized certification; no provisional markers remain).
Upstream PR/issue/comment: NONE. Linux validation: PENDING (authoritative
handoff: docs/phase5_1_r2/LINUX_FINAL_VALIDATION_HANDOFF.md).
