# R22A.2 — GFX1100 AdamW+AMP & Windows workers=8 Targeted Supplemental Validation

> **R22A.2.1 addendum (evidence completeness & fail-closed hardening)** — see
> [§8](#8-r22a21-evidence-completeness--fail-closed-hardening) below. Part A
> verdict unchanged; Part B verdict re-derived honestly as 2 COLD + 1
> CACHE_PRIMING + 2 WARM + 1 ADDITIONAL WARM. Raw evidence byte-frozen.

**Verdicts**

| Part | Verdict |
|---|---|
| A — DEFAULT `optimizer=auto` → AdamW + AMP multi-step | **ADAMW_AMP_MULTISTEP_PASS** |
| B — Windows DataLoader workers=8 short reliability (2 cold + 3 warm) | **WORKERS8_SHORT_RELIABILITY_PASS** |
| Combined | **R22A2_GFX1100_SUPPLEMENTAL_PASS** |

Maximum classification: `DEV_SUPPLEMENTAL_VALIDATED`. The accepted prior
`R22_DEV_DUAL_ARCH_VALIDATED` result is untouched; this mission only
strengthens DEV-stage training evidence. Nothing here promotes DEV to Stable.

## 1. Scope and base

- Repository: `AIwork4me/Ultralytics-Windows-ROCm-Training-RCA`
- Base: integration branch `work/windows-rocm-training-release-closure`
  @ `81477298bb25af892a457b57b4401e8c96fb9b15` (= previously verified HEAD,
  PR #16 merge). Feature branch:
  `feature/r22a2-gfx1100-adamw-workers8` (this PR).
- Host: Windows 11 build 10.0.26300, RX 7900 XTX (gfx1100), driver
  32.0.21030.2001, 24 logical CPUs.
- Stack (frozen lock `evidence/raw/r22-dev-rerun/resolved_wheel_lock.json`,
  46 artifacts, recomputed audit ok — families `[10]`, classes
  `{native_amd_gpu_stack: 8, approved_pypi_bootstrap: 1, third_party: 37}`):
  torch `2.15.0+gitf6cd88cb.devrocm10.3.0.dev0-ff576965…`,
  torchvision `0.29.2+gitb2281111.devrocm10.3.0.dev0.ff576965…`,
  rocm-sdk-libraries `10.3.0.dev0+ff576965…`, Ultralytics `8.4.214`
  (published PyPI wheel, unmodified), TheRock `ff5769655eeb1b91a46bce9edc16d87ca0efe7b6`
  embedded in every native version string.
- Loaded `MIOpen.dll` SHA256 `47a2e32c7401af2581860bc4a9e9fbb5b3f80be1e68c951b4ff3058f48683b91`
  — byte-identical to the accepted R22 dev-rerun evidence; PR#13437 marker
  count 2 (post-fix). Runtime class `OFFICIAL_CANDIDATE` in every GPU record.
- No non-goal gate was rerun (no G1 no-STL, no 9/9 GPU ops, no SGD audit, no
  checkpoint/resume marathon, no 10-run matrix, no gfx1151, no benchmarks).

## 2. Environment disclosure

A user-level `HIPRTC_COMPILE_OPTIONS_APPEND` shim variable (from the
YOLO26 Day1 labs work) is present on the host. It is **not** part of the
stack: every R22A.2 GPU process ran with the variable stripped at
orchestration (`env -u`) and `run_stability.py` additionally strips it from
child environments defensively. The user's global environment was not
modified. All records therefore classify `any_workaround_present = false`,
matching the exact condition of the accepted R22 dev-rerun evidence.
GPU was idle before/after (no external workloads; no foreign processes
terminated).

Isolated workspace `C:\RadeonYOLO\R22A2\` (scratch/logs/evidence/reports/cache).
Dataset: hermetic local copy of COCO128 under `cache/datasets/coco128` with an
absolute-path yaml; weights `yolo26n.pt`
(SHA256 `9b09cc8bf347f0fc8a5f7657480587f25db09b34bf33b0652110fb03a8ad4fef`)
pre-staged into each run dir — no network, no global cache touched.

## 3. Part A — `optimizer=auto` → AdamW + AMP (mission A1–A12)

Workload: YOLO26n, COCO128, epochs=3, batch=8, imgsz=256, device=-1,
workers=0 (isolates AdamW+AMP from worker behavior). **`optimizer="auto"`
was requested — never forced; normal `nbs=64` retained (effective
accumulate = 8 recorded, i.e. 48 batches → 6 optimizer updates; NOT forced to
step per batch).**

- **A1** `amp_resolved = true` (trainer AMP check passed).
- **A2** Resolved optimizer class **AdamW** (`torch.optim.AdamW`, `fused=True`;
  auto-resolution log line captured; lr 0.000119 = 0.002·5/(4+80), momentum
  0.9, per-group weight decay 0.0005/0/0). Ultralytics 8.4.214 heuristic:
  `iterations = ceil(128/max(8,64))·3 = 6 ≤ 10000` → AdamW (not MuSGD).
- **A3** **6 confirmed optimizer update events** (≥3) — confirmed by
  per-step parameter-checksum deltas, not by wrapper calls.
- **A4** Autocast active inside real forward: 48/48 forward-pre-hook samples
  with `torch.is_autocast_enabled() == True`.
- **A5** Actual dtype of eligible op under autocast recorded: every observed
  Conv2d output was `torch.float16`.
- **A6** Lower-precision compute observed: `torch.float16` (observed dtype,
  no assumed label).
- **A7** GradScaler present & enabled; full per-attempt scale history
  `65536→32768→16384→8192→4096·5→2048`, **5 backoff events** counted from
  per-attempt history (not inferred from endpoints).
- **A8** Finite-gradient check across ALL param groups with non-None grads at
  every step, per-step flags recorded (`grads_finite_all_steps=false` is the
  honest raw record — see A12 semantics).
- **A9/A10** `named_parameters()` before vs raw trainer model after:
  **366/366 tensors changed**, max |Δ| 2.51e-4, mean 2.40e-4, all finite.
  Post-train EMA-loaded model: 248/366 changed (EMA averaging, disclosed).
- **A11** BatchNorm running-stat buffers snapshotted separately (342 buffer
  tensors changed) and **never counted** as parameter-update evidence.
- **A12** **Fused-AdamW semantics handled explicitly**: with `fused=True`,
  `GradScaler.step` invokes the Python-level `optimizer.step` on every
  attempt and the inf/skip decision happens inside the fused kernel. A
  bounded 1-epoch diagnostic proved skipped steps leave the parameter
  checksum unchanged while Python-level calls continue. Update counting is
  therefore based on checksum deltas; the 5 nonfinite steps (post-clip NaN
  spread by `clip_grad_norm_` over inf grads) were skipped by the scaler
  exactly as designed, and every confirmed update had finite gradients
  (`grads_finite_at_confirmed_updates=true`). No wrapper call was counted as
  an update without supporting evidence.

Backward iterations: 48 (one per batch). Exit code 0; checkpoint
`last.pt` written (SHA256 in local ledger); training + final validation
completed; total wall 24.4s (warm cache).

**Execution attempts (honest disclosure):** attempt 1 failed on a harness
NameError (my scaler wrapper closure bug — log preserved); attempt 2 trained
fully but the contract misclassified fused-skip semantics as a gradient
failure (log preserved); attempt 3 PASS after the measurement fix. The system
under test never failed; the stack trained successfully in all three
attempts. A CPU regression test now pins the wrapper save/call name
consistency.

## 4. Part B — Windows workers=8 (mission §6–§8)

Workload per run: YOLO26n, COCO128, epochs=1, batch=16, imgsz=256,
device=-1, `workers=8`. COCO128 at batch=16 yields 8 batches, above the
`min(cpu//rank, workers, batches)` cap that would resolve COCO8 to 0 workers.

- Matrix: **cold 2/2 PASS + warm 3/3 PASS** (5/5; single execution per run,
  no reruns, no failures to mask).
- Cold = fresh isolated USERPROFILE per run (per-run distinct homes);
  warm = one deliberately retained shared isolated home (run 1 populated it —
  119s compile; runs 2–3 warm at 41s/25s; durations disclose which is which).
  Global MIOpen caches never touched.
- Effective workers verified two independent ways: child-reported
  `trainer.train_loader.num_workers == 8` in all 5 runs, plus **OS-level CIM
  process-tree snapshots** under the training PID (~0.8s cadence, 23–111
  samples/run): 13 distinct worker PIDs observed per run, peak 13 concurrent
  (train-8 + val-8 loader sets overlap; contract requires ≥8 observed).
  No private PyTorch implementation detail was used as sole proof.
- Process lifecycle: every run exit 0, `STABILITY_CHILD_DONE` marker,
  epoch + validation completed, checkpoint written, **0 orphan worker
  processes** at the +2s post-exit scan in all 5 runs; no python processes
  remained after the matrices. Bounded per-run timeout 600s (never hit).
- Windows spawn safety: the generated child now has a `main()` entry with
  `if __name__ == "__main__":` + `multiprocessing.freeze_support()`, so
  spawn re-imports cannot recursively start training. Verified by CPU
  contract tests (guard presence + compile) and by 5/5 clean runs. The
  historical workers=0 path is preserved byte-compatibly (default `--workers
  0`, same train kwargs, same classification flow).
- A spawn smoke test additionally proved DataLoader spawn works under
  `python -I` (module-level classes picklable; the child runs isolated).

## 5. Code changes (this PR)

1. `windows-golden-path/scripts/audit_adamw_amp.py` (NEW) — Part A audit;
   pure `evaluate_adamw_contract()` for CPU-testable acceptance.
2. `windows-golden-path/scripts/run_stability.py` — minimal extension:
   `--workers` (default 0), `--warm-home`, `--data/--batch/--imgsz`,
   Windows-safe child entry, OS worker observation, orphan scan, worker
   failure vocabulary (`WORKER_SPAWN_FAILURE`, `WORKER_INIT_FAILURE`,
   `WORKER_CRASH`, `WORKER_SHUTDOWN_FAILURE`, `DATALOADER_DEADLOCK`,
   `DATALOADER_TIMEOUT`, `GPU_OOM`), pure `evaluate_single_run()` /
   `evaluate_workers_matrix()`.
3. `windows-golden-path/tests/test_harness_cpu.py` — 41 new adversarial CPU
   contract tests (Part A + Part B + spawn-safety + wrapper-consistency
   regression). Existing 55 tests untouched: **96/96 pass**.
4. Frozen evidence under `evidence/raw/r22a2-gfx1100/` (23 files +
   SHA256SUMS.txt) and `windows-golden-path/reports/r22a2-gfx1100/`;
   manifest 197→220 entries; verifier re-run clean.

`audit_optimizer.py` (historical SGD test) is untouched; its frozen results
stand.

## 6. Independent review (mission §14)

1. **Did auto really choose AdamW?** Yes — trainer-resolved class `AdamW`,
   `fused=True`, auto-resolution log line, lr formula matches 8.4.214
   auto-fit; `trainer.args.optimizer` post-resolution captured as corroboration.
2. **Mixed precision inside real forward?** Yes — 48/48 forward samples under
   autocast during actual training forwards.
3. **Lower-precision compute observed?** Yes — Conv2d outputs `torch.float16`
   (sampled dtype, not assumed).
4. **Measurable parameter changes from successful optimizer calls?** Yes —
   366/366 tensors, max |Δ| 2.5e-4, checksum-confirmed updates 6.
5. **Gradients checked across all groups?** Yes — every step, all groups;
   per-step flags in evidence.
6. **Skipped scaler updates counted honestly?** Yes — 5 backoffs recorded;
   skipped steps excluded from update counts via checksum evidence; wrapper
   overcount disclosed (`11 python-level calls vs 6 confirmed`).
7. **Accumulation preserved?** Yes — nbs=64 default untouched; accumulate=8
   recorded; no per-batch forcing.
8. **Eight real worker processes?** Yes — `num_workers=8` resolved in-run +
   13 PIDs/peak-13 observed OS-level per run.
9. **All workers terminated cleanly?** Yes — 0 orphans ×5 runs; post-matrix
   system clean.
10. **Five runs independent?** Yes — separate processes, per-run dirs/seeds;
    cold homes distinct, warm home shared by design.
11. **Cold/warm honest?** Yes — cache class from actual USERPROFILE used;
    durations corroborate (119s vs 25–41s).
12. **Could a single failure be masked?** No — matrix logic: any FAIL/timeout
    → NO-GO; 4/5 + 1 fail → NO-GO (CPU-tested); no sixth run replaced
    anything.
13. **Frozen DEV stack only?** Yes — lock audit ok; MIOpen SHA identical to
    accepted baseline; shim var stripped; runtime OFFICIAL_CANDIDATE.
14. **Historical records untouched?** Yes — only additive dirs; prior
    evidence files unmodified (git diff confirms).
15. **Synthetic fixture → physical PASS?** Impossible — both contracts reject
    `harness_fixture` / missing GPU identity (CPU-tested).

## 7. Remaining external work

- AMD Stable wheel publication (stable channel still pre-fix/blocked).
- Stable dual-architecture acceptance (G7 gfx1151 on stable, G9 clean
  Windows) — unchanged.
- R23 developer-facing release packaging.

Evidence: `evidence/raw/r22a2-gfx1100/` (+ per-run child logs), checksums in
`SHA256SUMS.txt`, checkpoints local-only with SHA256 ledger
(`R22A2_CHECKPOINTS_LOCAL.json`). Machine verdict authority:
`R22A2_ACCEPTANCE_REPORT.json`.

## 8. R22A.2.1 — Evidence completeness & fail-closed hardening

**P0-A — restored the missing raw evidence.** The 8 files under
`evidence/raw/r22a2-gfx1100/runs/` (5 child logs, 2 matrix
`stability_runs.json`, 1 generated child source) were silently dropped from
the original commit by the repo-wide `.gitignore` rule `runs/` while
`SHA256SUMS.txt` had hashed the working-tree copies. Every file was verified
against its **frozen** SHA256SUMS value from the `C:\RadeonYOLO\R22A2`
originals before staging (`git add -f`); no synthetic replacements exist.
(The r21 `wheel-scan` pair flagged by a pre-scan was a false alarm from a
backslash path join — those files were committed since `3021e70`; the sums
parser now normalizes separators.)

**P0-B — verifier audits evidence against the exact Git tree.** New checks:
every `evidence/manifest.json` entry and every SHA256SUMS entry must resolve
to a **committed** file whose blob content matches the declared hash; a
checksum matching only a local/uncommitted file is a violation; missing
files → nonzero exit; `r22a2*` packs additionally require every committed
evidence file to carry a manifest entry; fail-closed when git/HEAD is
unavailable. This immediately caught and fixed a real pre-existing defect:
two r22a-gfx1151 manifest entries stale since `dfc3863` (hashes refreshed
with per-entry disclosure). Six new self-test scenarios (18/18) including a
gitignore-trap fixture reproducing the P0-A mechanism.

**P0-C — worker gate rejects anomalies even at exit 0.** `evaluate_single_run`
now scans the raw log for fatal signatures on every path. Exit 0 +
`hipErrorInvalidKernelFile` → NO-GO; exit 0 + DataLoader-worker crash →
NO-GO. The only matching pattern in the frozen logs — MIOpen
`EvaluateInvokers` "Invalid elapsed time" — is a documented **benign**
find-mode diagnostic (observed only in the two cache-priming runs, both
completed exit 0 with full training/validation); it is classified
(`MIOPEN_FIND_TIMING_DIAGNOSTIC`) with rationale and preserved verbatim,
never silently discarded. Re-scan of all five frozen child logs under the
hardened gate: **0 fatal, 5/5 PASS** (2 benign-classified).

**P0-D — matrix size and cache contract.** The strict contract now requires
exactly 2 COLD runs with distinct fresh homes, at most one CACHE_PRIMING run
on the shared warm home, and exactly 3 qualifying pre-warmed runs; unique run
identities; no duplicate/missing records; a single run can never satisfy it.
Honest re-classification of the original matrix: warm_run01 (119.1s, first
use of the fresh shared home) is **CACHE_PRIMING**, not a pre-warmed run —
the original "warm 3/3" wording over-counted. Corrected shape:
**2 COLD + 1 CACHE_PRIMING + 2 WARM**, which alone is NO-GO under the strict
criterion. Per the explicit P0-D allowance, exactly **ONE additional short
warm run** was executed on the committed hardened harness
(`home_pre_existed=true` recorded, 26.0s — genuine pre-warmed timing),
labeled **ADDITIONAL sample, not a replacement** for any earlier result.
Final matrix: 2 COLD + 1 PRIMING + 2 WARM + 1 ADDITIONAL = 3 qualifying
pre-warmed → `WORKERS8_SHORT_RELIABILITY_PASS` with roles
`[cold, cold, cache_priming, warm, warm, warm]`. All five original physical
records are byte-unchanged.

**P1 — timestamps and source identity.** Future runs record
`started_utc` at process launch, `finished_utc` after exit, and
`orphan_scan.scanned_at` at scan time (demonstrated on the additional run:
11:52:35 < 11:53:01 < 11:53:03). The frozen records' `started_utc` is NOT
overwritten — the reconciliation file records that it represents post-run
recording time. Source identity is now three-way distinguished:
integration base `8147729`; the frozen runs executed **uncommitted** harness
modifications (later committed as `78729e4`/`ee85a9b`); the additional run
executed committed `c07aa9b…`. See
`evidence/raw/r22a2-gfx1100/R22A2_WORKERS8_RECONCILIATION.json`.

**Final R22A.2.1 verdicts** — Part A: `ADAMW_AMP_MULTISTEP_PASS` (unchanged;
no contradicting evidence). Part B: `WORKERS8_SHORT_RELIABILITY_PASS`
(supported by complete logs: 6 runs, all committed, all rescanned under the
hardened gate). Combined: `R22A2_GFX1100_SUPPLEMENTAL_PASS`
(`DEV_SUPPLEMENTAL_VALIDATED`; no Stable claim). CPU contract 108/108;
verifier self-test 18/18; no historical raw evidence modified; failed-attempt
logs (`attempt1/attempt2`) preserved.
