# Phase 4 Summary — Windows Upstream Submission Preparation

Date: 2026-10-08. Execution platform: Windows 11 native (gfx1151,
ROCm 7.14.0 wheels, torch 2.12.0+rocm7.14.0).

## Objective and boundary

Produce a maintainer-quality submission package for the validated
P3-FINAL-R3 MIOpen HIPRTC self-containment fix — canonical commits, a
real CI regression test, a rebuilt-and-rerevalidated canonical MIOpen.dll,
final PR/maintainer documents, and four independent reviews — while
**creating no PR, issue, or comment anywhere upstream**.

## What was done (gates P40–P60)

| Gate | Result |
|---|---|
| P40 environment | verified; independent review CONDITIONAL PASS → items fixed (doc corrections) |
| P41 patch identity | SOURCE_SHA + both patch SHA256 + series SHA256 MATCH on origin/main; independent re-hash PASS |
| P42 upstream state | develop at `18e1985` (+37 commits), zero drift in all 8 affected files, no equivalent fix present, ordered series applies clean; review PASS |
| P43 source trees | baseline + canonical worktrees at exact SOURCE_SHA (longpaths enabled) |
| P44 canonical commits | `c86d1b9` + `4084759` via `git apply --index`; provisional identity, DCO-pending marker, no sign-off; review PASS |
| P45 semantic equivalence | **8/8 byte-identical** (blob OID + SHA256 + working-tree bytes; scope exactly 8 files); independent reconstruction PASS |
| P46 commit inspection | clean history/stats/whitespace; format-patch archived; `git am` round-trip 8/8 identical |
| P47 CI test design | `hiprtc_selfcontained.cpp`: strict controls, STL-unreachable probe, exact field-signature matching |
| P48 CMake/CTest | standalone build verified on Windows; upstream wiring proposal documented (not claimed as run in-tree) |
| P49 control matrix | 6/6 PASS (ordinary/positive/negative/with-stl × unpatched/patched); adversarial round 1 found 4 false-PASS vectors → hardened; re-verify found residual V1 → fixed (`fatal error:` anchor + error-count discipline); all attacks re-verified rejected |
| P50 canonical build | MIOpen.dll SHA256 `b32d6310817a225ff81cfe8de3dfe2a0d5c525caa845bad1f4d2304abc6aa721` (RelWithDebInfo, Phase-3 toolchain; wheel staged shim + 556 path-length-exempt gfx950 blobs removed during build, both restored) |
| P51 runtime binding | canonical DLL load PROVEN via GetModuleFileNameW + SHA256 inside the workload process; wheel hash-verified restored |
| P52 Windows regression | A GPU control PASS; B BatchNorm train/eval/backward PASS (max_abs 6.8e-7 vs CPU double); C no-STL validation PASS (MSVC include renamed, fresh profile/cache, canonical DLL proven); D numerics finite PASS; E YOLO26n coco8 1-epoch PASS in amp=False AND genuine default-AMP ("AMP: checks passed", amp=True) with weights saved |
| P53 Linux evidence | preserved, not rerun; identity chain verified (same base SHA + patch bytes → canonical == Linux-validated content); independent review PASS |
| P54 audit | authorship/DCO/copyright/format audited; classification PROVISIONAL LOCAL PACKAGE; clang-format finding recorded (no reformat applied to preserve byte-equivalence) |
| P55 documents | PR_DRAFT_FINAL.md, MAINTAINER_REPORT_FINAL.md |
| P56 final reviews | four independent reviewers (see below) |
| P57 packaging | manifest + security scan (findings/phase4/evidence_MANIFEST.json) |
| P58 RCA evidence branch | `phase4/windows-upstream-submission-prep` pushed to AIwork4me repo only |
| P59/P60 conclusion | findings/phase4/phase4_conclusion.json + final report |

## Deliverables map

```text
patches/phase4/canonical/        two-commit format-patch series (PROVISIONAL)
patches/phase4/ci_test_proposal/ hiprtc_selfcontained.cpp CI regression test
docs/phase4/                     all phase-4 documents
evidence/phase4/                 environment/identity/equivalence/build/
                                 windows_runtime/hiprtc_ci evidence + manifest
scripts/phase4/                  all reproducible runners
findings/phase4/                 reviews/ + conclusion + final gate
```

## Bottom line

```text
CROSS-PLATFORM VALIDATED FIX  →  CANONICAL, CI-TESTED, REBUILT,
RE-VALIDATED, REVIEWED PACKAGE  →  STOP — NO PR (by design)
DCO_PENDING_HUMAN_CONFIRMATION
readiness = READY_FOR_HUMAN_DCO

P56 final reviews: A APPROVE WITH CHANGES · B APPROVE WITH CHANGES ·
C NO REGRESSION FOUND · D APPROVE WITH CHANGES
Unresolved technical BLOCKER/MAJOR findings: 0
```
