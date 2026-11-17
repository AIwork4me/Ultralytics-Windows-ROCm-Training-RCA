# R22A.5N.1 Raw Evidence Completeness — recovery, disclosure, rerun closure

- Generated: 2026-11-17 (mission R22A.5N.1 PHASE 2 §5 / PHASE 5 §8.1)
- Rule applied: a referenced raw log either EXISTS in git (recovered original
  bytes or new envelope-captured bytes) or is declared
  `ORIGINAL_LOG_NOT_RECOVERABLE` and its gate re-proven by a NEW real GPU run.

## 1. Original pack A — referenced logs vs reality (cold audit findings)

| Receipt raw_log_path | Committed? | On host `C:\r22a5n`? | Disposition |
|---|---|---|---|
| `05_yolo_training_amp/adamw_amp.log` | no | **no** | ORIGINAL_LOG_NOT_RECOVERABLE → Stage C rerun |
| `07_reliability/workers8_amp.log` | no | **no** | ORIGINAL_LOG_NOT_RECOVERABLE (v1 run superseded by v2; v2 rerun covers the gate) |
| `07_reliability/workers8_amp_v2.log` | no | **no** | ORIGINAL_LOG_NOT_RECOVERABLE → Stage E rerun |
| `04_gpu_primitives/torchvision_ops.log` | no | **no** | ORIGINAL_LOG_NOT_RECOVERABLE → Stage C rerun |
| `06 …g5_resume\lifecycle_summary.log` | no | **no** | ORIGINAL_LOG_NOT_RECOVERABLE → Stage D rerun (v2 verifier now WRITES this file) |
| `02_runtime_identity` child.log (2 legs) | no | **yes** (713 B ×2) | RECOVERED → committed |
| `02_nostl_candidate` leg.log | yes | yes | byte-identical (verified) |
| `03_nostl_negative_control` v1/v2 leg.log | yes | yes | byte-identical (verified) |
| `06 stage1/stage3/stage4.log` | no | **yes** (18 421 / 22 166 / 277 B) | RECOVERED → committed |
| install logs (3) | yes | yes | real content (17 492 / 35 164 / 2 732 B) |

Root cause (instrumentation, now fixed): the training scripts set
`raw_log_path` to a **caller-side stdout redirect** they never wrote
themselves; the redirected files were never committed and later lost. The
R22A.5N.1 execution envelope (`scripts/r22a5n1/run_envelope.py`) owns
stdout/stderr capture at execution time, so this class of loss cannot recur.

## 2. Recovered originals committed (append-only)

`reports/r22a5n/R22A5N-GFX1151-20261117-A/raw_host_recovery/` — 21 files:
g5 stage1/3/4 logs + the three stage scripts, g0 child logs + reproducer
sources (both legs), all three no-STL leg logs, ultralytics `args.yaml` +
`results.csv` for amp_coco128 / lifecycle / workers8 / workers8_v2.
`RECOVERY_MANIFEST.json` records per file: source host path, bytes, SHA256,
source mtime, recovery time; the three leg logs are additionally proven
**byte-identical to their already-committed copies** (independent cross-check).
The original 29-entry `SHA256MANIFEST.json` is untouched.

## 3. Large binary artifacts (weights) — durable identity, honest disclosure

`WEIGHTS_SHA256_INVENTORY.json` (same directory) pins SHA256 + size of all
8 checkpoints plus `yolo26n.pt` still on the test host. These remain host-side
(44 MB total); they are NOT claimed as independently byte-verifiable from the
PR alone. Pack B additionally commits the Stage D lifecycle
`last.pt`/`best.pt` so the checkpoint gate IS independently verifiable there.

## 4. New physical runs (pack B) — every stage envelope-captured

`reports/r22a5n1/R22A5N1-GFX1151-20261117-B/stage_logs/<stage>_<ts>_<pid>/`
contains per attempt: `stdout.log` + `stderr.log` (original child bytes,
separate streams), `envelope.json` (command array, cwd, python exe, child PID
+ envelope PID/parent PID, start/finish UTC, duration, exit code, timed-out
flag, sanitized env subset incl. HIPRTC/MIOPEN/PYTHONPATH/PATH, git HEAD +
dirty files, CIM GPU identity, lock SHA, post-exit artifact hashes). Receipts'
`raw_log_path` references are satisfied by copies of these bytes placed next
to each receipt. Failed/intermediate attempts are retained, never overwritten
(unique per-attempt directory names).

## 5. Completeness matrix (final state after this mission)

| Gate | Raw evidence in git | Independent byte anchor |
|---|---|---|
| PKG | lock + frozen audit + manifests (packs A and B) | SHA256MANIFEST (A), evidence_pack verify (B) |
| LK | receipts + lock bytes | engine re-hash (LK gate) |
| G0 | child.log + reproducer (A recovered, B captured) | pack manifests |
| G1 | leg.log ×3 + reproducer (A recovered; B ×3 captured) | pack manifests |
| G2 | torchvision_ops.log (B captured; A declared lost) | pack B manifest |
| G3/G4 | adamw_amp.log (B captured; A declared lost) | pack B manifest |
| G5 | stage1/3/4 logs (A recovered) + full v2 lifecycle (B) + checkpoints (B) | pack B manifest |
| G7 | workers8 logs (B captured; A declared lost) + census/orphan (A+B) | pack manifests |

No mandatory gate any longer rests on an unavailable raw log; the five losses
are each closed by a same-contract new physical run rather than by inference.
