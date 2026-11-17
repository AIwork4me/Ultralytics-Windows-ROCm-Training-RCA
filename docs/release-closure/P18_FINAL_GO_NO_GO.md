# P18 FINAL GO/NO-GO — Second-Architecture (gfx1100) PR Validation

**Date**: 2026-11-15 · **Hardware**: AMD Radeon RX 7900 XTX (gfx1100), Windows 11 26300, driver 32.0.21030.2001

## Final conclusions (mission §12, strictly separated)

| Conclusion | Verdict |
|---|---|
| A. PR #27198 GFX1100 SOURCE VALIDATION | ✅ **GFX1100_VALIDATED** (B1 ✓, B2 9/9 ✓, B3 ✓, B4 ✓, B5 SKIP w/ root cause = the other PR) |
| B. PR #27203 GFX1100 SOURCE VALIDATION | ✅ **GFX1100_VALIDATED** (C1–C9 ✓ incl. CVD matrix; C8 3/3 PASSED) |
| C. COMBINED GFX1100 SMOKE VALIDATION | ✅ **PASS** (D1–D9 incl. hard-kill + new-process resume; F 7/7 stability) |
| D. OFFICIAL GFX1100 GOLDEN PATH | ⛔ **BLOCKED_RELEASE** (10.1.0 MIOpen wheel still lacks #13437 — live-verified; PRs unmerged) |
| E. PHYSICAL MULTI-GPU MAPPING | ⛔ NOT_RUN (single RX 7900 XTX; SINGLE_GPU_VISIBILITY_PASS only) |
| F. NVIDIA WINDOWS REGRESSION | ⛔ NOT_RUN (no NVIDIA GPU; nvidia-smi success branch contract-verified only) |

A+B+C all PASS → **both PRs: `GFX1100_PHYSICAL_SOURCE_VALIDATED`** — second-architecture evidence established.

Cross-architecture roll-up: gfx1151 (P17) + gfx1100 (P18) independent source validations → **TWO_ARCH_SOURCE_VALIDATION_COMPLETE** for these two PRs. This is NOT `OFFICIAL_TWO_ARCH_USER_GOLDEN_PATH_COMPLETE` (gate D remains blocked for both architectures pending AMD wheel fix + upstream merges).

## Maintainer-review readiness

Both PRs, at the exact heads validated here (`e5ac8593` / `563ff46e`):

- ✅ minimal diffs at correct owners; no new deps/args; no broad except beyond repo-tolerated style (BLE001 CI-ignored)
- ✅ Ruff clean under the CI-exact command; `ruff format --check` clean; CI fully green at head (incl. windows-latest)
- ✅ real-hardware evidence on TWO architectures (gfx1151 P17 + gfx1100 P18), AMP/FP32/train/resume/stability all green
- ✅ NVIDIA healthy paths preserved (success branch byte-identical; probe-only change in #27198)

**READY_FOR_MAINTAINER_REVIEW: YES** for both PRs. Not claimed merged/accepted.

## Environment caveats future missions must know

1. SAC (Smart App Control) flipped ON by the 2026-11-13 cumulative update and blocks ALL unsigned AMD ROCm DLLs + uv venv trampolines. It was disabled by the user on 2026-11-15 (cannot be re-enabled without Windows reset). If a future reset re-enables it, GPU work will block again the same way.
2. torch split-wheel trap now confirmed on the **torchvision** side too: `torch[device-gfx1100]` does not pull `amd-torchvision-device-gfx1100`; symptom = `hipErrorInvalidDeviceFunction` at `torchvision.ops.nms` during val.
3. ultralytics ≥8.4.2xx needs `polars` at checkpoint save (`read_results_csv`).
4. github.com:443 had a ~40-min outage on 2026-11-15; api/codeload stayed up.

## Raw evidence index

All logs under `evidence/raw/p18/` with SHA256 in `evidence/manifest.json`; results JSONs `p18_pr27198_results.json`, `p18_pr27203_results.json`, `p18_combined_results.json`; environment freeze `P18_ENVIRONMENT_AND_PROVENANCE.json`; verifier output before/after push recorded below.
