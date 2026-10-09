# Gate C2 — Independent Subagent Audit (Phase 5.2.1)

Reviewer: fresh-context adversarial subagent, read-only audit + one
authentic re-measurement. Full matrix re-verified.

## Sub-check verdicts

a. Patch integrity & worktree — **PASS**
   3 canonical sha256s re-hashed from the freeze ref (14719b8b… /
   7d40c314… / 3eb20ec0…); worktree log = 7c5866144a + 3 patch commits;
   write-tree = 605d0d214acdbc06086fdb27c61fec970c0f2798. Patch commit
   bodies verified identical to the frozen series (only email signature
   and index lines differ).
b. Patch-0003 hunk & exit-code contract — **PASS**
   Registration inside if(MIOPEN_USE_HIPRTC) via manual add_test_command;
   zero SKIP_RETURN_CODE / SKIP_ / WILL_FAIL matches in the patch; exit
   contract 0/1/2/4; mandatory STL probe returns kExitInconclusive(4).
c. BUILD_TESTING=OFF facts — **PASS**
   legA CMakeCache:30 BUILD_TESTING:BOOL=OFF; build_leg_miopen.sh:49;
   upstream gating CMakeLists.txt:967-968.
d. Exit-code matrix from committed logs — **PASS** (byte-for-byte)
   positive=4 (STL_PROBE_REACHABLE + INCONCLUSIVE), negative=4,
   with-stl=0 (6048-byte code object), ordinary=0 (code_size=3824);
   ctest: 0% passed / 1 failed / CTEST_EXIT_CODE=8; discovery Test #10.
e. Live re-measurement — **PASS**
   Reviewer re-ran the test binary: POSITIVE_EXIT=4 (identical
   INCONCLUSIVE diagnostic), WITH_STL_EXIT=0 (identical 6048-byte code
   object). (Reviewer noted env errexit needs set +e — measurement
   artifact, not an evidence problem.)
f. F-C2-2 mechanism — **PASS**
   hiprtc-targets.cmake defines ONLY hiprtc::hiprtc with
   INTERFACE_INCLUDE_DIRECTORIES; no plain hiprtc target anywhere;
   workaround flags present in the build cache; wrapper copies identical;
   flag-delta vs Leg A wrapper = BUILD_TESTING + 2 disclosed workarounds
   + isolated install prefix only.
g. Over-claiming / frozen-patch integrity — **PASS**
   rca-evidence tree clean; patches/ untouched; evidence JSON states
   inconclusive_counted_as_pass=false. Hazard noted (see below).

## Notes (non-blocking)

1. Dual patch series coexist on main's working tree (superseded
   patches/phase5/canonical vs frozen patches/phase5_1/canonical on the
   freeze ref) — documented delta; confusion hazard addressed by the
   SOURCE-OF-TRUTH note added to the findings doc.
2. Reviewer's reverse-apply order artifact (0003→0002→0001 required);
   resolved via commit-body diff.

## Overall verdict: **APPROVED-WITH-NOTES**

Every falsifiable claim reproduced exactly, including the live exit-4 and
exit-0 re-measurements with identical code-object byte counts and the
package-level mechanism of F-C2-2. INCONCLUSIVE is nowhere counted as
PASS. The single reservation (dual series hazard) is mitigated by the
pointer note now present in CTEST_PORTABILITY_ANALYSIS.md.
