# Phase 5 — Final Gate (P5-18)

```text
PHASE 5 — UPSTREAM SUBMISSION FINALIZATION
Status: PHASE5_WINDOWS_COMPLETE — DCO_OR_COPYRIGHT_PENDING
                  + LINUX_FINAL_REVALIDATION_PENDING
```

## Gate-by-gate

| Gate | Result | Evidence |
|---|---|---|
| P5-00 preflight | PASS | evidence/phase5/environment/preflight.json |
| P5-01 baseline freeze | PASS (P3 hashes match; P4 canonical verified) | environment/baseline_freeze.json |
| P5-02 upstream applicability | PASS (develop 7c58661; zero drift; no duplicate; series applies) + independent review PASS | docs/phase5/UPSTREAM_BASE_ASSESSMENT.md, reviews/P502 |
| P5-03 isolated candidate | PASS (8/8 pre-cleanup equivalence) | source_delta/pre_cleanup_equivalence.json |
| P5-04 maintainer polish | PASS (5 fixes: 4 applied, copyright PENDING) + adversarial review CONDITIONAL PASS (nothing executable changed) | SOURCE_CHANGE_JUSTIFICATION.md, reviews/P504 |
| P5-05 candidate identity | PASS (P5-CANDIDATE-R1; audited delta) | PATCH_IDENTITY.json, P3_TO_P5_DELTA.md |
| P5-06/07 CI test + CMake/CTest | PASS 4/4 (configure/build/discovery/run) | CI_INTEGRATION.md, evidence/phase5/ci |
| P5-08 adversarial A/B | PASS 13/13 + false-PASS attack: no CI-config false-PASS vector; hardening F1/F3/F4 applied post-attack and reverified | ci_matrix_phase5.json, reviews/P508 |
| P5-09 final MIOpen.dll | PASS sha256 d5974dad… | build/build_provenance.json |
| P5-10 DLL load provenance | PASS (GetModuleFileNameW+SHA256 in-process) | runtime/dll_provenance.json |
| P5-11 no-STL runtime | PASS (MSVC include renamed; fresh profile; provenance held) | runtime/nostl_validation.json |
| P5-12 numerics | PASS (y 6.71e-07 vs Phase-4 ref 6.85e-07; running stats ~1e-10; all finite; tolerances fixed pre-run) | runtime/runtime_validation.json |
| P5-13 YOLO26n | PASS amp=False AND default AMP (genuine: "AMP: checks passed", amp=True; weights saved; provenance per run) | yolo/yolo_train.json |
| P5-14 Linux implications | handoff complete; LINUX_PHASE5_TARGETED_REVALIDATION = PENDING | LINUX_FINAL_VALIDATION_HANDOFF.md, PATCH_HANDOFF.json |
| P5-15 history + DCO audit | PASS (identity/email verified via GitHub API linkage; DCO + copyright deliberately PENDING) | AUTHORSHIP_DCO_AUDIT.md |
| P5-16 PR draft + report | complete; Background & Motivation review: content 6/6 PASS (96 words), evidence claim resolved | PR_DRAFT_FINAL.md, MAINTAINER_REPORT_FINAL.md, reviews/P516 |
| P5-17 four reviews | A CONDITIONAL PASS (human items only) / B CONDITIONAL PASS (M1 fixed) / C PASS / D CONDITIONAL PASS (items completed in this gate) + amendment re-check PASS 7/7 | reviews/P517_* |
| P5-18 this file | conclusion + manifest generated | phase5_conclusion.json, evidence_manifest.json |

## Runtime-evidence provenance note

Runtime gates (P5-10..P5-13) executed at commit `39319c4d`; the final
tip is `29846fc4` after the post-panel amendment. The amendment's delta
is test-only (`projects/miopen/test/`), and the `projects/miopen` src +
include trees of the two commits are byte-identical (verified as check 7
of the amendment re-check). MIOpen.dll `d5974dad…` therefore remains
the validated artifact for the final candidate. The CI gates were
re-executed AT the final commit (4/4 + 13/13).

## Human actions outstanding

1. DCO sign-off decision (exact commands: AUTHORSHIP_DCO_AUDIT.md §3).
2. Copyright attribution for the FOUR placeholder files (3 headers +
   test source), then targeted revalidation.
3. Linux targeted revalidation (PATCH_HANDOFF.json).
4. Submission-day develop re-check (Gate P5-02 method).

## Upstream state

```text
UPSTREAM PR CREATED: NO
UPSTREAM ISSUE CREATED: NO
UPSTREAM COMMENT POSTED: NO
INTERNAL PR CREATED: NO
```
