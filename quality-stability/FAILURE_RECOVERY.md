# FAILURE RECOVERY — G4.3 observed failure/recovery behaviors

## Observed and handled during this mission (real events, real recoveries)

1. **Interrupted training → resume (7/7 tasks)**: callback-exception interruption after epoch 1 of 4; separate process resumed from `last.pt` and completed all planned epochs. Resumability precondition verified (`epoch=1` + optimizer state present).
2. **Force-killed GPU process**: hard-killed probe left an unkillable zombie (driver-level); subsequent GPU processes ran unaffected — isolation between processes holds on this stack. Costs: locked env-B DLL (restore deferred), documented in `windows-training-validation/environment/INCIDENT_ZOMBIE_PROCESSES.md`.
3. **Exit-time hang**: 1 of ~20 GPU processes hung after producing results (exit-time HIP cleanup); results were already flushed — no data loss; new work unaffected.
4. **MIOpen solver-timing errors mid-training**: `EvaluateInvokers … elapsed <= 0` logged during ENV B conv solves — training **continued to completion** (logged error, not fatal); consequence characterized in G3 (kernel-selection instability), not a crash path.
5. **Network failures mid-mission**: GitHub push failures (retried OK later); S3 download stalling (recovered via 8-segment Range download with byte-exact verification — imagenette sha256 recorded); all failures recovered with verified artifacts, none silently swallowed.

## Recovery rules encoded in the harnesses

- Every leg writes JSON incrementally or at stage boundaries; a crash preserves partial evidence.
- All subprocess exit codes are checked explicitly (runners abort on non-zero with log pointers).
- No exception swallowing anywhere in the new harnesses; first errors surface with full text.
- Cache-home isolation per leg prevents cross-leg state contamination (and provided the control variable for the G3 cache-state discovery).

## NOT_RUN (honest)

- GPU OOM recovery (workloads too small); Windows multi-GPU DDP (out of scope, single iGPU); OS-level crash recovery (no crash occurred).
