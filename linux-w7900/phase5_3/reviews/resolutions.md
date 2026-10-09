# Gate L12 — Final Four-Reviewer Panel: Verdicts, Findings, Adjudication, Resolutions

Panel composition (four FRESH independent subagents, launched after all gates L00–L11 closed):

| Reviewer | Focus | Session | Verdict |
|---|---|---|---|
| A | MIOpen upstream maintainer | ses_edfcc03c4ffeIIVWyBS6d33eIO | CONDITIONAL PASS |
| B | GPU runtime validation | ses_edfcbe415ffeoHB2GZS6AjEBHZ | PASS |
| C | Source and binary integrity | ses_edfc6e818ffeG8lfYLiywGUZB1 | PASS |
| D | False-pass / submission quality | ses_edfc6b6c6ffe5AeDe2B75wxPfg | PASS (endorses PHASE5_3_LINUX_R2_AB_PASS_WITH_CTEST_SKIP) |

## Reviewer A blockers — adjudication

**A-B1 (DCO unsigned; no authorization to submit upstream).**
ADJUDICATED: NOT a mission blocker — the mission explicitly withholds DCO sign-off and
upstream PR authorization ("NOT AUTHORIZED: DCO sign-off, upstream PR submission"), and the
frozen R2 manifest records `authorization_to_submit_upstream: false` and
`dco_status: UNSIGNED_BY_DESIGN`. The Linux validation's obligation is to REPORT this
boundary honestly, which it does. Recorded as an upstream-merge-readiness CONDITION
PRECEDENT in docs/UPSTREAM_MERGE_READINESS.md (human action required before any PR).
No frozen artifact may be changed to "fix" this on Linux.

**A-B2 (no-STL positive control never executes on any Linux host).**
ADJUDICATED: NOT a mission blocker — this is the exact condition for which the mission
defines the verdict `PHASE5_3_LINUX_R2_AB_PASS_WITH_CTEST_SKIP`: "PASS_WITH_CTEST_SKIP is
appropriate if all required Linux build/runtime/numerical checks PASS and the only relevant
test limitation is genuine, documented Linux no-STL isolation unavailability." L07 proves
the skip is genuine (probe fires, exit 4, fixture-verified mapping, honest "did not run"
reporting). The Windows no-STL ground truth remains the Windows RCA's claim. Recorded as
the second upstream-readiness condition precedent.

## Reviewer A majors — adjudication (coverage-bounding, documented, none block the mission)

- **A-M1** (freestanding initializer_list arm compile-tested nowhere in default suite;
  tensor_view.hpp RTC consumers uncovered by ctest): TRUE — documented in
  UPSTREAM_MERGE_READINESS.md coverage boundaries. The Phase-3/5.2 A/B harnesses
  (kthvalue via radix.hpp) and this mission's L08 cover the radix/tensor_view headers at
  RUNTIME on both legs; the ctest gap is an upstream-improvement request, not a Linux
  validation defect.
- **A-M2** (radix int32/int64 encode branches never executed; BF16 kthvalue untested):
  TRUE — scope boundary documented. The changed lines are datatype-generic template code
  shared by the executed FP32/FP16 instantiations; documented as untested-dtype boundary.
- **A-M3** (skip-policy duplication vs add_test_command refactor): upstream review
  preference; recorded as a likely upstream objection (no frozen-patch change possible
  without a new Windows candidate revision).
- **A-M4** (no full gtest suite on the patched leg; no conv/pooling A/B): scope boundary
  documented; YOLO smoke (B-leg, conv-heavy) partially compensates and is explicitly
  labeled non-A/B.

## Reviewer B findings — resolutions

- MINOR-1 (L09 stale A5/B5 prefetch refs) → RESOLVED: strings corrected to A6/B6.
- MINOR-2 (pre-fix L09 logs not archived) → RESOLVED: explicit non-retention note added
  to L09 evidence.
- MINOR-3 (CK grouped-conv library shared across legs) → RESOLVED: documented in L08
  evidence (`ck_shared_library_note`); CK-solver claims out of leg-isolation scope.
- NIT (HIPRTC "v9.0" non-discriminating string) → isolation rests on dladdr provenance
  (present in every runtime gate); noted.

## Reviewer C findings — resolutions

- MINOR-1 (65-char hash typo propagated in published phase5_2 evidence B08/B09/runbook):
  historical published artifacts must NOT be rewritten; ERRATUM added in
  phase5_3/docs/PHASE5_3_SUMMARY.md cross-referencing the L00 length analysis. The
  true 64-char digest (b830b37a…e7ef8) is pinned in L00/L08 and verify_final_evidence.py.
- MINOR-2 (legB binary hash bf21a5fa unpublished until phase5_3 commit) → RESOLVED by
  Gate L13/L14 (this evidence package pins it).
- NIT-4 (local leg-B commit SHAs differ from manifest ordered_commits) → expected
  (committer metadata); recorded in L01/L03 evidence and UPSTREAM docs.

## Reviewer D findings — resolutions

- MINOR-1 (L09 stale refs) → same fix as B-MINOR-1.
- MINOR-2 (L08 lacks interpretation note) → RESOLVED: `interpretation_note` added.
- MINOR-3 (original erroneous L08 JSON not archived) → RESOLVED: explicit
  `original_fail_json_note` added (non-retention disclosed, mechanically guarded).
- NIT-1 (dead `verdict_consistent` in checker) → RESOLVED: removed; checker re-run
  26/26 PASS.
- NIT-2 (compound verdict strings) → normalized in FINAL_LINUX_VALIDATION.json verdicts.
- NIT-3 (empty docs/findings at review time) → populated by Gate L13.

## Panel conclusion

No unresolved BLOCKER or MAJOR within the mission's authorized scope. The two Reviewer-A
"blockers" are upstream-submission governance conditions that the mission explicitly
places OUT of scope (no DCO, no PR) and which are recorded as conditions precedent for any
future upstream action. All required Linux build/runtime/numerical checks PASS; the sole
test limitation is the genuinely documented Linux no-STL isolation unavailability.

**Final verdict: PHASE5_3_LINUX_R2_AB_PASS_WITH_CTEST_SKIP.**
