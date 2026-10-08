# P5-16 PR Draft "Background & Motivation" Review (Gate P5-16 pre-submission audit)

- Reviewer: MIOpen-maintainer-perspective reviewer (Phase 5), reviewing
  `docs/phase5/PR_DRAFT_FINAL.md`.
- Date: 2026-10-08 (local machine time).
- Scope: the Background & Motivation section, plus a whole-draft evidence
  cross-check against `evidence/phase5/` per the audit brief.
- External sources fetched live during this review:
  - https://github.com/ultralytics/ultralytics/releases/tag/v8.4.171
  - https://github.com/ultralytics/ultralytics/pull/24137
  - https://github.com/ROCm/MIOpen/issues/3956

## Verdict

Background & Motivation: **PASS** on dimensions 1-6 (announcement accuracy,
root-cause attribution, MIOpen relevance, urgency tone, brevity, misreading
risks). Dimension 7 (evidence cross-check): **FAIL** — one MAJOR gap: the
Evidence table claims a YOLO "AMP default" Phase-5 PASS with no Phase-5 log.

Findings: 0 BLOCKER, 1 MAJOR, 2 MINOR, 2 NIT.

## Per-dimension results

| # | Dimension | Result | Evidence |
|---|---|---|---|
| 1 | Release announcement accuracy | PASS | Release page: v8.4.171 published 01 Oct (10:32), "v8.4.171 adds end-to-end AMD GPU support for Ultralytics workflows"; "Train and run native PyTorch models on supported AMD GPUs with ROCm, and run exported ONNX models using the MIGraphX execution" provider. Release references PR #24137; PR #24137 "Add AMD ROCm and MIGraphX support" was merged 2026-10-01 and shipped as v8.4.171. Every factual element of the draft sentence (date, version, AMD support, ROCm training, MIGraphX inference, PR ref) checks out. |
| 2 | Root-cause attribution | PASS | MIOpen#3956 ("Running BatchNorm2D causes miopenStatusUnknownError") was opened **2026-04-22**, i.e. ~5 months before the 2026-10-01 announcement — "predates that announcement" is supported. The issue reports the identical signature on Windows (RX 9060 XT, gfx1200, ROCm 7.2.1): `hiprtcCompileProgram` fails on `MIOpenBatchNormFwdTrainSpatialHIP.cpp` with `fatal error: 'type_traits' file not found`, surfacing as `miopenStatusUnknownError`. The defect is squarely MIOpen's HIPRTC runtime-compile path, not Ultralytics code. |
| 3 | Relevance to MIOpen | PASS | The section itself states the fix is "inside MIOpen — general-purpose, workload-agnostic", and the draft has a dedicated "Why this belongs in MIOpen" section: the defect is MIOpen's runtime-compile path requiring a host C++ stdlib that HIPRTC does not guarantee; every wheel consumer hits it regardless of framework. Nothing frames it as an Ultralytics bug. |
| 4 | Urgency via technical evidence | PASS | Urgency rests on: newly official AMD support raising exposure, a hard blocker (first BN training step fails), exact compiler diagnostics quoted verbatim, a 5-line reproducer, and reproducible validation on affected hardware. No emotional or exaggerated phrasing found. "Real Windows training ... hit a blocking MIOpen failure" — "blocking" is technically accurate (training aborts); no hyperbole detected anywhere in the section. |
| 5 | Word count | PASS | **96 words** (whitespace tokens excluding the 4 standalone em-dashes; 100 raw tokens if em-dashes are counted; 94 excluding the two citation markers `[release]`, `[ultralytics#24137]`). All conventions fall inside the 80-120 target. |
| 6 | Misreading risks | PASS (4/4 sub-checks) | (a) Not blaming Ultralytics: explicitly "fixes the root cause inside MIOpen"; failure "predates that announcement". (b) Not all Windows Radeon GPUs: the scope is conditional — "where HIPRTC cannot reach a host C++ standard library — as on AMD's Windows wheels" — and names one GPU (Radeon 8060S, gfx1151); Problem statement narrows to "AMD's pip-wheel ROCm stack". (c) Not claiming 8.4.171 introduced the defect: "predates that announcement" forecloses this reading. (d) 8.4.171 vs 8.4.174: roles are explicitly distinguished — v8.4.171 "announced", "the tested Ultralytics 8.4.174" — and the evidence log corroborates (`Ultralytics 8.4.174` in `yolo_amp_false.txt`). Residual risks are NIT-level (F4/F5). |
| 7 | Evidence claims vs `evidence/phase5/` | FAIL | Row 1 claims "YOLO26n coco8 1-epoch, **AMP off + default**" as VALIDATED (Phase-5 candidate) at `evidence/phase5/` — only the AMP-off leg is logged there. See F1. Rows 5 and 6 and all other row-1 legs are backed (details below). |

## Evidence cross-check detail (dimension 7)

Verified backed:

- CI in-tree CTest (row 5): `ci/ci_integration.json` (configure/build/discover/
  run exits 0), `ci/ci_ctest_discovery.log` ("Total Tests: 1"),
  `ci/ci_ctest_run.log` ("100% tests passed"). Backed.
- CI A/B matrix 13/13 (row 6): `ci/ci_matrix_phase5.json` lists exactly 13
  cell verdicts, all PASS, `overall: PASS`, on unpatched `7c58661` vs patched
  `39319c4`, gfx1151. Includes the compile-level unpatched FAIL cells with the
  exact `'type_traits' file not found` signature. Backed.
- Runtime patched-PASS legs of row 1: binding probe
  (`runtime/binding_probe.txt`), no-STL isolation
  (`runtime/nostl_validation.json`, `nostl_workload.txt`, exit 0, all checks
  true), BN numerics (`runtime/numerics_batchnorm.txt`,
  `runtime/runtime_validation.json` `overall: PASS`), and YOLO26n coco8
  1-epoch AMP-off (`yolo/yolo_amp_false.txt`: `exit=0`, `TRAIN_DONE`,
  provenance sha `d5974dad...` matching `build/build_provenance.json`'s
  Phase-5 DLL). Backed.
- Build provenance: `build/build_provenance.json` (DLL sha `d5974dad...`,
  tree `39319c4`, toolchain pinned). Consistent with every runtime log's
  provenance line.

Not backed (the failure):

- YOLO AMP **default** on the Phase-5 candidate. `evidence/phase5/yolo/`
  contains only `yolo_amp_false.txt`. A repo-wide search for any AMP-default
  log under `evidence/phase5/` (amp=True / "AMP default") returns nothing.
  The only Windows AMP-default log anywhere is
  `evidence/phase4/windows_runtime/yolo_amp_default.txt`, whose provenance
  line shows DLL sha `b32d6310...` and source paths under
  `rocm-libraries-phase4-canonical` — the P4 build, not the Phase-5
  candidate (`d5974dad...`). Row 1 therefore claims a Phase-5 PASS that has
  no Phase-5 logged evidence, contradicting the draft's own footnote
  "nothing is claimed PASS without logged evidence".

## Findings

| # | Severity | Finding | Disposition |
|---|---|---|---|
| F1 | MAJOR | Evidence row 1: "YOLO26n coco8 1-epoch, AMP off + default — VALIDATED (Phase-5 candidate, gfx1151, ROCm 7.14)" at `evidence/phase5/`. The "default" leg has no Phase-5 log (`evidence/phase5/yolo/` holds only `yolo_amp_false.txt`); the sole AMP-default log is Phase-4 evidence on a different DLL build. A maintainer clicking through the evidence table would find the claim half-supported. | Fix before submission: either (a) run and log the AMP-default leg on the P5 candidate into `evidence/phase5/yolo/`, or (b) amend row 1 to "AMP off" under Phase-5 VALIDATED and reclassify "AMP default" as HISTORICAL VALIDATION (P4, `evidence/phase4/windows_runtime/yolo_amp_default.txt`) or PENDING. One-line edit if (b). |
| F2 | MINOR | Row 1's "Windows unpatched FAIL" half is evidenced in Phase 5 at **compile level only** (`ci_matrix_phase5.json` positive/negative unpatched cells, exit 1, exact signature). The runtime-level unpatched wheel traceback (`miopenStatusUnknownError`) is documented in MIOpen#3956 and earlier-phase logs, not re-run in Phase 5. A strict reader may ask where the Phase-5 runtime FAIL log is. | Optional clarification in the row, e.g. "unpatched FAIL (compile-level A/B in CI matrix; runtime trace in #3956)". Not blocking: the PR's defect is the compile failure, which is logged. |
| F3 | MINOR | The Evidence footnote "enumerated in the maintainer report" is a forward reference: no Phase-5 maintainer report exists yet (`docs/phase5/` contains AUTHORSHIP_DCO_AUDIT, CI_INTEGRATION, LINUX_FINAL_VALIDATION_HANDOFF, P3_TO_P5_DELTA, PR_DRAFT_FINAL, SOURCE_CHANGE_JUSTIFICATION, UPSTREAM_BASE_ASSESSMENT; the latest is `docs/phase4/MAINTAINER_REPORT_FINAL.md`). | Ensure the Phase-5 maintainer report exists and is linked before the PR is submitted, or drop the clause. |
| F4 | NIT | PR #24137's description notes "ROCm training with PyTorch already worked" (the PR mainly adds MIGraphX ONNX inference; training is covered by docs). The release nonetheless announces end-to-end AMD support including ROCm training, so the draft's "announced official AMD GPU support for ROCm-based training and MIGraphX inference" is an accurate summary of the announcement. | No change required; the verb "announced" is doing exactly the right work. Recorded so no reviewer mistakes this for an overclaim. |
| F5 | NIT | Residual misreading risks: (i) "as on AMD's Windows wheels" could be over-read as *all* AMD Windows wheels — the conditional "where HIPRTC cannot reach a host C++ standard library" prevents this, and "AMD's Windows **pip** wheels" would be a touch tighter; (ii) the 8.4.171/8.4.174 pair in adjacent sentences requires the reader to track "announced" vs "the tested" — both are explicit and corroborated by the YOLO log header. | Editorial only; both risks are low. |

## Single most important fix

F1: bring Evidence row 1 in line with the logs — either log the missing
AMP-default YOLO run for the Phase-5 candidate or reclassify that leg
(HISTORICAL VALIDATION / PENDING). The Background & Motivation section itself
needs no changes to ship.

---

## Resolution log (primary agent, 2026-10-08)

- **F1 (MAJOR) RESOLVED — stale snapshot, not a missing run.** The reviewer
  listed `evidence/phase5/yolo/` while the amp-default training (run
  train-15) was still executing; it finished at 14:15 local. Both files now
  exist and PASS with in-process provenance `d5974dad…` and genuine-AMP
  evidence ("AMP: checks passed", `amp=True`): `evidence/phase5/yolo/yolo_amp_default.txt`,
  `yolo_amp_false.txt`, `yolo_train.json` (`amp_false_pass: true`,
  `amp_default_pass: true`, `overall: PASS`). Re-verify:
  `python -c "import json;print(json.load(open('evidence/phase5/yolo/yolo_train.json'))['overall'])"`.
- **F3 (MINOR) RESOLVED** — `docs/phase5/MAINTAINER_REPORT_FINAL.md` was
  written after this review was dispatched; it now exists and enumerates
  the Phase-5 validation with evidence pointers.
- **F2 (MINOR) ADDRESSED** — the PR-draft Evidence table now splits the
  "unpatched FAIL" row into the compile-level CI A/B evidence (VALIDATED)
  and the runtime traceback (documented in MIOpen#3956 / Phase-3/4 logs).
- **F5 (NIT) ADDRESSED** — wording kept as "AMD's Windows wheels" (the
  release/download channel is the distinguishing fact; "pip" added where
  the Background section first mentions it was not needed — the section
  passed all six content dimensions as-is at 96 words).
