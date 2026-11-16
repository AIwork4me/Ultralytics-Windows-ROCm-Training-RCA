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

## Non-comparison (by contract)

Raw wall-times are NOT compared between the APU (Radeon 8060S, shared memory) and the
dGPU host: bandwidth, memory topology, driver paths and TDP differ (mission §14). No
performance claim is made in either direction.

## Decision

Shared snapshot identical + all gates pass on both architectures ⇒
**R22_DEV_DUAL_ARCH_VALIDATED** (project-internal DEV-level verdict; NOT an
OFFICIAL_STABLE_PASS, NOT R23_RELEASE_READY — Stable remains gated on a stable-channel
artifact + G9 clean-Windows evidence).
