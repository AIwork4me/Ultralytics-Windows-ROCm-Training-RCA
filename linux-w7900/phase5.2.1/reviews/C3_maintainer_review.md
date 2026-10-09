# Gate C3 — Independent Maintainer-Style Review (Phase 5.2.1)

Reviewer: fresh-context subagent simulating an upstream MIOpen maintainer;
re-verified load-bearing mechanics in an isolated scratch CMake project
(two-call set_tests_properties merge; SKIP_RETURN_CODE exit-4 vs exit-1;
target-name-in-COMMAND with EXCLUDE_FROM_ALL; -R/--output-on-failure).

## Load-bearing claims independently verified (all hold)

- F-C2-3: MIOPEN_TEST_GDB default On (test/CMakeLists.txt:96); non-WIN32
  branch wraps with cmake -P + message(FATAL_ERROR "Test failed") — exit
  code destroyed before CTest sees it; confirmed by C2_ctest_run.log.
  "SKIP_RETURN_CODE necessary but not sufficient" is correct.
- set_tests_properties two-call form MERGES (no clobber).
- SKIP_RETURN_CODE semantics: exit 4 → ***Skipped/Not Run; exit 1 →
  ***Failed rc 8 (re-executed by reviewer). Genuine regressions still
  fail.
- add_test(NAME ... COMMAND <target-name>) resolves to the executable.
- F-C2-2: hiprtc package defines only hiprtc::hiprtc; impl target
  survives plain name via hip::host; if(TARGET ...) capability-correct,
  no-op delta on Windows.
- WORKING_DIRECTORY drop harmless: test reads only argv-derived absolute
  kernel path; hiprtc compiles in memory.
- Mission boundaries: tree clean; nothing under patches/ touched;
  freeze-ref 0003 re-hashes to 3eb20ec0…; Windows PASS evidence intact.

## Findings (all resolved in the proposal, see resolutions)

1. MINOR — skip-list/allowlist bypass undisclosed → DISCLOSED BEHAVIORAL
   DELTAS section added (with optional parity guard noted).
2. MINOR — "exit 4 never occurs on an isolating host" contradicted by
   P5-08 CPATH cell → requirement matrix reworded.
3. MINOR — F-C2-2 raw failure output not in committed logs → evidence
   note added; re-freeze checklist step 4 now requires capturing it.
4. MINOR — alternatives table missing MIOPEN_TEST_GDB=OFF and mixed
   registration rows → rows 7 and 8 added with rejections.
5. NIT — stale in-patch comment after Hunk 1 → checklist step 1 updated.
6. NIT — silent WORKING_DIRECTORY drop → disclosed with rationale.
7. NIT — "set the skip property once" wording → reworded (merge noted).
8. NIT — CI_INTEGRATION.md docs drift → checklist step 3 updated.
9. NIT — line-wrap artifacts → fixed.
10. NIT — DCO placeholder → checklist step 1 requires resolution before
    any upstream submission.

## Overall verdict: **RECOMMEND-WITH-CHANGES**

No technical claim could be falsified; the design is capability-based,
minimal, keeps Windows verdicts untouched and makes Linux honest. All
findings were disclosure-quality fixes (applied to
CI_AMENDMENT_PROPOSAL.md in this branch before publication); none
required rethinking the mechanism.
