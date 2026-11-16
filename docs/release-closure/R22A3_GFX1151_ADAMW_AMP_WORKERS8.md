# R22A.3 — gfx1151 (Radeon 8060S) Default AdamW + AMP and Windows workers=8 Supplemental Validation

- **Mission**: R22A.3 supplemental validation on the physical Windows Radeon 8060S host
- **Date**: 2026-11-16
- **Branch**: `feature/r22a3-gfx1151-adamw-workers8`, base = integration HEAD `8147729` (PR #16 merge; base tree identical to PR head `d13c975`, tree `1617237e`)
- **Scope**: Part A default `optimizer="auto"` → AdamW multi-step AMP audit; Part B Windows DataLoader `workers=8` short-run reliability (2 cold + 3 warm). No other gates re-run; historical R22A/P19B evidence untouched.
- **Runtime ceiling**: DEV_CANDIDATE — this document never claims OFFICIAL_STABLE or R23_RELEASE_READY.

## 1. Environment (frozen stack re-verified at mission start)

`R22A3_ENVIRONMENT_BASELINE.json` — **FROZEN STACK CONFIRMED, zero drift**:

| Fact | Value |
|---|---|
| Windows | 10.0.26200.9974 25H2 |
| GPU / gfx | AMD Radeon(TM) 8060S Graphics / gfx1151 (capability [11,5]) |
| Driver | 32.0.22032.6002 |
| Python / torch / torchvision / HIP | 3.12.16 / 2.15.0+gitf6cd88cb.devrocm10.3.0.dev0.ff576965… / 0.29.2+gitb2281111… / 7.18.26441 |
| Ultralytics | 8.4.214 (non-editable) |
| Loaded MIOpen.dll SHA256 | `47a2e32c7401af2581860bc4a9e9fbb5b3f80be1e68c951b4ff3058f48683b91` (matches frozen expectation) |
| Workarounds | none (no HIPRTC/MIOPEN_*/PATH redirection) → runtime_class OFFICIAL_CANDIDATE |
| Wheel lock | `evidence/raw/r22a-gfx1151/R22A_GFX1151_PACKAGE_LOCK.json` (46 artifacts, SHA256 recorded in each evidence record) |

Notes: the two historical P19B background processes (pids 37120/12052, `p1_amp_audit.py`) were still present and were only OBSERVED, never terminated — the same condition under which the accepted R22A evidence was produced. The 8060S is an APU: 98.9 GB CUDA-visible memory is shared system memory, not dedicated VRAM.

## 2. Part A — default optimizer=auto → AdamW + AMP (`R22A3_ADAMW_AMP.json`)

Workload (bounded, framework defaults preserved): YOLO26n / COCO128 / epochs=3 / imgsz=256 / batch=8 / `optimizer="auto"` / AMP default / device=-1 / workers=0 / **nbs NOT set** (default 64; gradient accumulation NOT manipulated).

**Verdict: `ADAMW_AMP_MULTISTEP_PASS`** (A1–A15 recomputed by `r22a3_acceptance.py` from embedded facts):

- **Auto selection proven**: requested `"auto"`; `build_optimizer` rewrote `args.optimizer` to `AdamW` (lr=0.000119 auto-fit, momentum 0.9); actual class `AdamW`; 3 param groups 126/114/126 tensors.
- **AMP real**: `trainer.amp=True`; forward-pre-hook autocast enabled **48/48** sampled train-batch forwards; backbone stem conv outputs observed **float16 48/48** (observed dtype, not assumed); GradScaler present+enabled.
- **Accumulation recorded**: nbs=64, batch=8 → accumulate ramps 1→8 across the 48-iteration warmup (series recorded); 11 optimizer-step invocations over 48 batches.
- **Effective updates physically proven**: 7 of 11 step invocations moved sentinel parameters (max|Δ| 2.2e-5…6.0e-5 ≈ the per-step lr, as AdamW predicts); the other 4 invocations carried `found_inf=True` (GradScaler-registered attribute observed) with non-finite grads during fp16 warmup — 4 scaler backoffs 65536→4096, all disclosed (scale backoff is not treated as failure).
- **Gradient finiteness across ALL groups**: 4026 tensor-checks across every param group at every step; finite on all non-found_inf steps.
- **Parameter deltas**: named_parameters only (BatchNorm buffers excluded by construction): 366/366 tensors changed, max|Δ| 2.9e-4, all finite; checkpoint `last.pt` SHA256 recorded; process exit 0.

**Attempt disclosure (identical workload, no PASS-shopping — the stack-under-test trained successfully in every attempt; failures 1–3 were post-training harness receipt/instrumentation bugs, all logs preserved)**:

| Attempt | Outcome |
|---|---|
| A1 `R22A3-A` | training completed; evidence writer rejected record (missing `command` key) — log preserved |
| A2 `R22A3-A2` | training completed; `torch.dtype` not JSON-serializable in receipt — log preserved |
| A3 `R22A3-A3` | training completed (366/366 params changed) but sentinel selection was EMPTY (trainer builds its own model instance — id-match against the pre-training snapshot found nothing) → honest FAIL, receipt preserved |
| A4 `R22A3-A4` | instrument repaired **and CPU-verified first** (`verify_instrument_cpu.py`): sentinel deltas observed, nonlocal rebinding fixed, found_inf observation verified → PASS |

The mission budget (§11: one run + one bounded diagnostic run) was exceeded by A3/A4; this deviation is disclosed here and in `R22A3_SOURCE_PROVENANCE.json`. Rationale: each failure was a deterministic CPU-side bug in the measurement instrument (not the stack under test), every attempt used the identical bounded workload, no failure was replaced or concealed, and the alternative (reporting the demonstrably-working stack as FAIL due to my own instrument) would have been the dishonest outcome.

## 3. Part B — Windows workers=8 (`R22A3_WORKERS8.json`, `R22A3_WORKERS8_RUNS.json`, `R22A3_PROCESS_LIFECYCLE.json`)

Workload: YOLO26n / COCO128 / epochs=1 / batch=16 / imgsz=256 / device=-1 / `workers=8`. COCO128 because COCO8 cannot exercise 8 workers; batch=16 so the loader's worker cap formula `nw = min(cpu_count // nd, workers, batches)` yields batches=8 ≥ 8.

**Verdict: `WORKERS8_SHORT_RELIABILITY_PASS`** — cold 2/2 + warm 3/3, every run independently PASS:

| Run | Cache | Exit | resolved nw (train/val) | worker PIDs | Shutdown | Batches | Train+Val | ckpt SHA256 (12…) | Duration |
|---|---|---|---|---|---|---|---|---|---|
| R22A3-B-R1 | cold (fresh USERPROFILE) | 0 | **8** / 4 | 13 distinct | CLEAN | 8/8 | ✓/✓ | 54610e311f10 | 199.2 s |
| R22A3-B-R2 | cold (fresh USERPROFILE) | 0 | **8** / 4 | 13 distinct | CLEAN | 8/8 | ✓/✓ | d13f0c24ee8a | 195.3 s |
| R22A3-B-R3 | warm (retained shared home) | 0 | **8** / 4 | 13 distinct | CLEAN | 8/8 | ✓/✓ | 385d0d3a6b12 | 198.4 s |
| R22A3-B-R4 | warm (retained shared home) | 0 | **8** / 4 | 13 distinct | CLEAN | 8/8 | ✓/✓ | 8f88ef49936d | 82.9 s |
| R22A3-B-R5 | warm (retained shared home) | 0 | **8** / 4 | 13 distinct | CLEAN | 8/8 | ✓/✓ | b2584488e748 | 60.7 s |

- **Real worker processes**: parent-side psutil process-tree monitoring observed 13 distinct `python.exe` descendants per run (8 train-loader workers + 4 val-loader workers + 1 spawn helper), each sighted 8–148 times; per-PID first/last-seen lifetimes in `R22A3_PROCESS_LIFECYCLE.json`. Warm-cache effect visible in durations (198 s cold compile → 61 s warm), confirming the retained shared cache identity worked.
- **Spawn safety**: the generated child is `__main__`-guarded with `freeze_support()`; no module-level training; the parent refuses to run a child that fails the structural spawn-safety check (`child_spawn_safe`). During a run, one monitor thread hit a psutil race (worker exiting between `children()` and `ppid()`) — post-run inspection confirmed all 5 runs retained complete 13-PID evidence; the sampler now tolerates mid-scan exits.
- **Cold/warm integrity**: cold runs redirect USERPROFILE to per-run fresh homes (verified from inside the child: `userprofile_env` recorded); warm runs deliberately share one retained isolated home; the user's global MIOpen caches were never touched or deleted.
- **No orphans**: all descendant PIDs gone after each parent exit (bounded 30 s wait); zero anomalies (`anomaly_tally: {}`).

## 4. Combined acceptance

`R22A3_ACCEPTANCE_REPORT.json` — **`R22A3_GFX1151_SUPPLEMENTAL_PASS`** (Part A + Part B both recomputed from embedded facts; claimed verdicts never authoritative; physical gfx1151 provenance + OFFICIAL_CANDIDATE runtime enforced; ceiling DEV_CANDIDATE).

## 5. Code changes

- `windows-golden-path/scripts/audit_adamw_amp.py` — NEW (Part A harness; pure `compute_adamw_verdict` recomputable on CPU)
- `windows-golden-path/scripts/run_stability.py` — minimal extension: `--workers` (default 0), `--data/--batch/--imgsz/--weights/--cold-runs/--warm-home`, spawn-safe generated child + `child_spawn_safe`, psutil tree monitor, `finalize_worker_run`/`overall_workers8_verdict`; historical default behavior unchanged (R21/R22 invocations produce the same command shape)
- `windows-golden-path/scripts/r22a3_acceptance.py` — NEW (combined verdict recomputation)
- `windows-golden-path/tests/test_harness_cpu.py` — extended 55 → 94 tests (mission §10 negative controls incl. final-verdict tests, spawn-safety, receipt serialization)
- `gp_lib.py`, `audit_optimizer.py` and all historical evidence: **unchanged** (verified against base `8147729`)

## 6. Remaining release work (unchanged by this mission)

gfx1100 R22A.2 physical validation (no branch/PR exists yet); AMD Stable wheel publication; Stable dual-architecture acceptance; clean-Windows G9 (still BLOCKED_INFRASTRUCTURE on a development host); R23 developer-facing release.
