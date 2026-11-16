# R22A Dual-Arch Comparison — gfx1100 (dGPU) vs gfx1151 (APU)

Mission R22A §14 deliverable. Machine-readable companion: `R22A_DUAL_ARCH_MATRIX.json`.
gfx1100 side reads ONLY frozen evidence (`evidence/raw/r22-dev-rerun/`,
`windows-golden-path/reports/r22-dev-rerun-orchestrated/report.json`); gfx1151 side is
this mission's live run (`evidence/raw/r22a-gfx1151/`).

## Build identity

| Item | gfx1100 | gfx1151 | Verdict |
|---|---|---|---|
| TheRock snapshot | `ff5769655eeb…` | `ff5769655eeb…` | identical |
| torch | `2.15.0+gitf6cd88cb.devrocm10.3.0.dev0.ff576965…` cp312 | same version string, cp312 | identical |
| torchvision | `0.29.2+gitb2281111…ff576965` | same | identical |
| Ultralytics | 8.4.214 (PyPI) | 8.4.214 (PyPI) | identical |
| rocm-sdk-libraries wheel SHA256 | `dac27df5…` | `dac27df5…` | **byte-identical** |
| embedded MIOpen.dll | `3.6.3.4e7d93e3` | `3.6.3.4e7d93e3` | identical build |
| arch device wheels | `amd-*-gfx1100` + `rocm-sdk-device-gfx1100` | `amd-*-gfx1151` + `rocm-sdk-device-gfx1151` | arch-specific (expected) |

Shared-package diff (43 packages incl. torch/torchvision/rocm-sdk-core/rocm-sdk-libraries/
rocm-bootstrap): versions AND SHA256 identical in every case. Dependency differences: none.
Fix ancestry (both): TheRock `ff576965` → rocm-libraries submodule `4e7d93e3` →
GitHub compare vs merged fix `f0a5d266`: ahead_by 604, **behind_by 0** (re-verified live
for gfx1151 at audit time via compare + git-trees APIs).

## Behavioral gates

| Gate | gfx1100 (frozen) | gfx1151 (live) |
|---|---|---|
| G1 no-STL MIOpen #13437 regression | OFFICIAL_CANDIDATE_PASS | OFFICIAL_CANDIDATE_PASS (cold cache, VCToolsInstallDir hidden) |
| G2 torch/torchvision GPU ops | PASS | PASS |
| G3 exact CLI `device=-1` | PASS (selects Radeon dGPU) | PASS (selects CUDA:0 = Radeon 8060S, AMP check PASSED, checkpoints hashed) |
| G4 real AMP optimizer update | PASS | PASS (184 steps, 359/366 tensors changed, grads finite at every step, per-step scaler history) |
| G5 interrupt/resume lifecycle | PASS | PASS (resume=True semantics, 3 processes) |
| G8 cold reliability | 10/10 PASS | **10/10 PASS** (116–136 s/run, anomaly tally empty) |
| G8 warm supplement | n/a | 3/3 PASS (29–33 s/run; reported separately, not counted as cold) |

## Evidence reconciliation (R22A.1 P1)

Full note with per-item source paths and original SHA256 values:
`R22A_EVIDENCE_RECONCILIATION.md` (same directory). Summary of what it fixes
in the derived records — no raw log was rewritten; both
`SHA256SUMS.txt` manifests still validate:

- **gfx1100 G8 cold**: matrix field `g8_cold` was a `null` placeholder while
  the MD already said 10/10 — now filled from frozen
  `evidence/raw/r22-dev-rerun/gpH_stability.json`
  (`GP-G-20261116-080547`, 10/10 PASS, all `cold(fresh-USERPROFILE)`).
- **gfx1151 G5 resume**: matrix fields `epochs_continuity` / `resume_process`
  / `inference_third_process` were `null` placeholders — now filled from frozen
  `gpF_resume.json` (`GP-F-20261116-093332`): rows_at_kill 3 → final_epoch_rows
  9, `resume_state_evidence_logged=true`, `epoch_continuity=true`, third-process
  infer OK — genuine resume-state (training state) evidence, 3 processes.
- **gfx1151 loaded MIOpen identity**: now recorded explicitly (SHA256
  `47a2e32c…`, build `3.6.3.4e7d93e3`, marker 2, identical to the
  wheel-embedded DLL) from `gpA_provenance.json`.
- **G3 original vs parser-derived**: the accepted G3 PASS
  (`gpD_train_cli.json`) traces to the attempt-2 raw stdout
  (`gpD_train_stdout.log`); attempt 1's fail-closed NO-GO (env-prep `runs_dir`
  displaced checkpoints out of the gate scan; training itself exited 0,
  mAP50 0.941) is preserved unmodified in `attempt1_g3_first_failure/`.
- **Package-origin contract**: both frozen 46-artifact locks (45 wheels + 1
  official ROCm source distribution) keep their historical
  `gpu_stack_origin_official_channel.ok=false` / `violations=["rocm-bootstrap"]`
  bytes; the corrected R22A.1 P0 policy (approved pure-Python PyPI bootstrap =
  exact pinned artifact; native stack = exact official channel; PyPI never
  supplies torch/torchvision/rocm-sdk-libraries/device wheels) recomputes both
  locks to PASS — enforced by CPU regression test
  `TestPackageOriginPolicy::test_frozen_dev_locks_pass_corrected_validation`.

## Non-comparison (by contract)

Raw wall-times are NOT compared between the APU (Radeon 8060S, shared memory) and the
dGPU host: bandwidth, memory topology, driver paths and TDP differ (mission §14). No
performance claim is made in either direction.

## Decision

Shared snapshot identical + all gates pass on both architectures ⇒
**R22_DEV_DUAL_ARCH_VALIDATED** (project-internal DEV-level verdict; NOT an
OFFICIAL_STABLE_PASS, NOT R23_RELEASE_READY — Stable remains gated on a stable-channel
artifact + G9 clean-Windows evidence).
