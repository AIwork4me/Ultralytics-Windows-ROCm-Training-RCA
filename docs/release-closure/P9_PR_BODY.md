# P9 — Final Evidence Hardening (test correctness, provenance, upstream readiness)

Closes the residual correctness, provenance and upstream-readiness gaps from the P8 independent audit. Every claim below links to raw evidence committed in this branch; the verifier (565 checks, exit 0) recomputes verdicts from embedded assertion data and rejects known-bad synthetic records.

## §3.1/3.2 — t07/t08 rewritten + t16 (audit B-F2, M5, C13 closure)

- `windows-training-validation/tests/amp_step_audit.py`: per-parameter tensor-delta optimizer-step verification (float64 max-abs per tensor; aggregate `Σ|θ|` cancellation trap proven caught), strict AMP gradient health (no unconditional PASS — scaled-domain non-finite acceptable ONLY as a scaler-sanctioned skipped step), full GradScaler instrumentation (found_inf via the torch≥2.4 method API, skip decision, scale transitions), honest classification `WARMUP_SKIP/OVERFLOW_SKIP/UPDATED/STUCK_FAILURE/BAD_GRAD_UPDATE`.
- CPU adversarial suite `test_amp_step_audit_cpu.py` **34/34** — caught 4 real instrumentation bugs before any GPU run.
- ENV A official-wheel re-run (`raw/g2_detect_amptrack_20261114T131559Z.json`, in-process DLL `e97891df…`): **14/15 PASS + 1 honest SKIP**; historical t08 FAIL reclassified per-step as intended overflow skips; **t16 = 24 genuine repeated updates** (366/366 tensors changed per update, scaler anneal 65536→2048).
- Log-collision defect fixed: immutable `run_id`-keyed outputs everywhere.

## §3.3 — G4 epoch accounting root cause

"31 callbacks for 30 epochs" = 30 training epochs + 1 upstream `final_eval()` epoch+1 best-metrics callback (verified in 8.4.174 AND 8.4.182 source). Harness rewritten with configured-vs-observed reconciliation, in-process DLL probe, embedded results.csv (audit B-F9), wall samples, checkpoint metadata. **G4 re-run on ENV A and ENV B** (`raw/g4_long_run_ENV_{A,B}_p9.json`) — third-environment caveat eliminated; matched A/B: ENV A AMP valid (1.43× epoch time, VRAM −33%); ENV B check_amp fallback honestly labeled (`amp_leg_valid=false`, no ratio claimed).

## §3.4 — verifier v2 + adversarial fixtures

`scripts/verify_release_closure.py`: 565 checks — assertion recomputation, SKIP≠PASS enforcement, per-env DLL consistency (contamination detector), run/env-ID cross-log consistency, hardware consistency, G4 reconciliation enforcement, claims→evidence citation checks. `scripts/test_verify_release_closure.py`: known-good tree accepted + **11 violation classes all REJECTED (12/12)**. Fresh-checkout run: exit 0.

## §4.2 — AMP precheck: upstream already redesigned; validated here

**Discovery**: ultralytics **8.4.197 (PR #26967, 2026-11-01)** replaced `amp_allclose` with a per-layer relative-norm check — our drafted PR-C is obsoleted (no duplicate patch submitted). Evidence suite built anyway: IoU matcher (`amp_iou_matcher.py`, class-constrained injective matching, IoU≥0.95 + scale-sensitive absolute bound + conf≤0.05) with CPU adversarial suite **26/26** + archived real tensors **5/5** + GPU captures on both cache states with **all 5 negative controls caught on real tensors**. **New-check validation on gfx1151**: 8.4.212 `check_amp` PASS on ENV A default (11.8s) + warm-training context; ENV B results in `raw/g3_checkamp84212_*.json`.

## §4.4 — genuine AMP learning (representative dataset)

Matched FP32-vs-AMP classify on imagenette2-160 (6 epochs): FP32 887 updates top1 0.935→0.973; **AMP 887 updates top1 0.935→0.970 (Δ−0.23%), 1.25× faster** (`raw/g3_amp_learning_ENV_A_official.json`); ENV B AMP leg honest SKIP (fallback). Audit M5's "not weight-learning" caveat is closed by 887 per-parameter-verified updates.

## §4.3 — EvaluateInvokers: RCA unresolved (per mission), issue ready

Minimal no-Ultralytics reproducer: **0 occurrences in 18 probes** across both environments (fresh-cache Find path, subprocess-attributed). Issue draft `upstream-readiness/MIOPEN_EVALUATEINVOKERS_ISSUE_V2.md` hands the in-context evidence (4× ENV B + 1× official aborted attempt) to maintainers without guessing.

## §5.1/P10 — full 7-task FP32 matrix re-run on the new harness

detect/segment/classify/pose/obb/semantic/depth **14/14 PASS each** + detect workers 2/4 14/14 (in-process DLL `ed7c67a9…` per task).

## Release status

Official-wheel rescan 2026-11-14: newest Windows wheel remains torch-2.12.0+rocm7.14.1 → **BLOCKED_RELEASE stands** (GO-A/B upgraded CONDITIONAL PASS; GO-C NO-GO on external blocker).

## Verdicts

GO-A **CONDITIONAL PASS (upgraded)** · GO-B **CONDITIONAL PASS (upgraded)** · GO-C **NO-GO (BLOCKED_RELEASE, external)** — see `GO_NO_GO.md` P9 addendum and `FINAL_REPORT.md` §K.
