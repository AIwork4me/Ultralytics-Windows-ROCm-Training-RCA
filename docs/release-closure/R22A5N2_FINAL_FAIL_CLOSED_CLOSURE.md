# R22A.5N.2 — Final Fail-Closed Gate Closure (G5 Resume Semantics × G7 Worker Provenance)

- Mission: R22A.5N.2 (CPU-only, minimal, fail-closed). PR #22 stays Draft for owner review.
- Base: R22A.5N.1 @ `568981d` (`R22A5N1_GFX1151_NIGHTLY_EVIDENCE_AUDITED_PASS`, 311 CPU tests).
- Scope: `scripts/r22a5n1/nightly_acceptance.py`, `windows-golden-path/tests/test_r22a5n1_cpu.py`,
  this note, one `.gitattributes` line for the new derived-report namespace.
  Pack A/pack B bytes, manifests and all physical evidence untouched.

## G5 — fail-closed resume semantics

Defects closed (both allowed a PASS on incomplete evidence):

1. `epoch_continuity_recomputed` degraded to `None` (→ tolerated) whenever
   `total_epochs` was missing, and missing `rows_at_kill` / `resume_start_epoch`
   were silently coerced (`or 0`, `is None → accept`).
2. `FULL_TRAINING_STATE_RESTORE_PASS` was awarded while the scheduler was
   recorded `NOT_SERIALIZED_BY_UPSTREAM` — absence of state evidence was
   being counted as restoration evidence.

Rules now enforced (all recomputed from the receipt's own numbers):

- Required epoch evidence: `total_epochs` (pos int), `rows_at_kill`,
  `final_epoch_rows` (non-neg ints), `resume_start_epoch` (≥1),
  `last_epoch_value`, `checkpoint_resumability.ckpt_epoch`,
  `resume_exit` (==0), `resume_effective_updates` (≥1). Missing/invalid ⇒
  FAIL with `epoch_evidence_missing` / `epoch_evidence_invalid` facts.
  `bool` is never accepted as an int (`True` ≠ 1).
- Continuity: `last_epoch_value == total_epochs` (CSV epoch column is 1-based
  display; checkpoint `epoch` key is 0-based — observed Ultralytics semantics,
  no invented off-by-one), `final_epoch_rows > rows_at_kill` (new epoch
  observations after resume), `resume_start_epoch == ckpt_epoch + 1`,
  `1 ≤ resume_start_epoch < total_epochs` (never reset to initial state).
- Stored `epoch_continuity=True` is only diffed; the numeric recompute is
  authoritative.
- Classification: `SERIALIZED` (key exists in checkpoint) and
  `RESTORE_VERIFIED` (independent post-resume evidence) are distinct claims.
  `FULL_TRAINING_STATE_RESTORE_PASS` requires every mandatory class
  (model_weights, optimizer, epoch, best_fitness, trainer_args, emma,
  gradscaler, scheduler) to be both serialized AND restore-verified.
  With Ultralytics 8.4.214 (scheduler not serialized, GradScaler `scaler` key
  serialized but not restore-verified) the honest ceiling is
  `RESUME_PASS_CORE_STATE_VERIFIED`, and G5 still PASSes on it.

## G7 — worker identity & parentage from raw snapshots

Defect closed: the gate trusted the stored `spawn_children_of_trainer` PID
list (count + uniqueness); a forged PID list could pass without any per-worker
verification against raw process data.

Rules now enforced (recomputed from `snapshots[].python_tree` only):

- Every counted worker must appear in ONE snapshot's own tree as a direct
  child of the trainer (`PPID == trainer_pid`), with genuine
  `from multiprocessing.spawn import spawn_main` semantics, and a cmdline
  `parent_pid` (when present) equal to the recorded PPID.
- Simultaneity: only the peak single snapshot's valid workers count — PIDs
  scattered across different-time snapshots never add up; ≥8 required.
- Trainer must exist in the peak snapshot's tree and chain to the REQUIRED
  execution-envelope PID through a cycle-guarded PPID ancestry walk.
- Stored PID list/counts (`spawn_children_of_trainer`,
  `spawn_children_count`, `spawn_main_children_count`) are only DIFFED against
  the recomputation; any mismatch fails the gate.
- Orphan check recomputed: only the RECORDED pre-start baseline
  (`baseline_python_pids`, cross-checked against the census disclosure and the
  envelope's own baseline) may excuse survivors; the census disclosure must
  agree with it; a baseline PID shown by the census tree to be the trainer's
  own child is a forged baseline (contradiction); trainer and every attributed
  worker must be absent from the post-run PID set regardless of any list;
  leftover = all − baseline − checker. Stored `orphan_verdict` is never read.
- Worker roles (train/val) are not claimed — the evidence does not identify them.

## Verification (all executed)

| Check | Result |
|---|---|
| New G5/G7 adversarial tests (31 added: 15 G5 + 16 G7, incl. 2 recomputing directly from committed pack-B bytes) | PASS |
| Full CPU suite `windows-golden-path/tests` | 342 PASS (311 baseline + 31 new), 0 FAIL, 0 SKIP |
| `scripts/verify_release_closure.py` | ok=true, 902 checks, 0 violations |
| `compileall` (windows-golden-path, scripts/r22a5a, scripts/r22a5n1) | PASS |
| Ruff (default rules, no repo lint gate) | 7 pre-existing findings before and after — 0 new |
| Pack B SHA256MANIFEST verify (`evidence_pack.py verify`) | ok=true, 106/106 entries, 0 problems |
| Pack A SHA256MANIFEST (29 files) | 0 hash mismatch, 0 missing |
| `git status reports/` | clean — packs byte-identical, zero modification |
| Pack B acceptance rerun (engine `r22a5n2-fail-closed-acceptance-v3`) → `reports/r22a5n2/R22A5N2-GFX1151-20261117/nightly_acceptance.json` | PKG/LK/G0/G1/G2/G3/G4/G5/G7 all PASS; overall `R22A5N1_GFX1151_NIGHTLY_EVIDENCE_AUDITED_PASS`; G5 = `RESUME_PASS_CORE_STATE_VERIFIED` (scheduler `NOT_SERIALIZED_BY_UPSTREAM`); G7 = 16 workers independently verified (trainer 39592 → envelope 6784, single snapshot 2026-11-17T05:18:34Z, trainer + all workers terminated, leftover = []) |
| Clean-clone repeat | run at the pushed HEAD; see PR #22 R22A.5N.2 summary |

The stricter gate made authentic evidence *harder* to pass, not easier — and
the real physical pack B still passes every check without any relaxation.
