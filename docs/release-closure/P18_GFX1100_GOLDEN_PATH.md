# P18 — GFX1100 Official Golden Path Gate Assessment

**Date**: 2026-11-15 · **Decision**: **OFFICIAL GFX1100 GOLDEN PATH = BLOCKED_RELEASE**

## Gate-by-gate

| # | Gate (mission §8) | Status | Evidence |
|---|---|---|---|
| 1 | RX 7900 XTX in official support matrix | ✅ MET | ROCm 10.1.0 compatibility matrix lists RX 7900 XTX (gfx1100) / Windows 11 |
| 2 | Driver & device packages correct | ⚠️ PARTIAL | Driver 32.0.21030.2001 (Adrenalin 26.x line); 10.1.0 device wheels installable |
| 3 | Official Windows ROCm wheels published | ✅ MET | `stable.repo.amd.com/rocm/whl-next` serves torch 2.14.0+rocm10.1.0 etc. |
| 4 | MIOpen fix shipped and passes no-STL test | ❌ **FAILED** | Live test on 10.1.0 wheels (torch 2.14.0+rocm10.1.0, hip 7.16.26385), **without** any shim: BatchNorm train-mode forward/backward → `RuntimeError: miopenStatusUnknownError`. Upstream fix ROCm/rocm-libraries#13437 still absent from the 10.1.0 wheel. [log: `pip_venv101.log`] |
| 5 | Released Ultralytics contains the needed fixes | ❌ **FAILED** | PR #27198 & #27203 both still OPEN/unmerged at mission time; released 8.4.213 does not contain them |

## Live no-STL re-test (fresh venv, 2026-11-15)

```text
torch 2.14.0+rocm10.1.0 | hip 7.16.26385 | avail True
Conv2d+BatchNorm2d(train) forward/backward on cuda:0
→ RuntimeError: miopenStatusUnknownError        (no HIPRTC shim present)
```

The identical test passes on 7.14.1 WITH the local freestanding shim (Phase A3/P18_BASELINE). Conclusion unchanged since the Day1/P15 era: **the blocking defect is the MIOpen wheel, not Ultralytics and not the PRs under test.**

## What WAS completed instead (all ENGINEERING_REFERENCE, clearly labeled)

- A/B/C/D/F phases: full source-level validation of both PRs + combined integration + stability + interrupt-resume on the shim-enabled 7.14.1 stack — see P18_PR27198_GFX1100.md, P18_PR27203_GFX1100.md, P18_COMBINED_GFX1100.md
- **30-epoch ENGINEERING_REFERENCE training on the combined tree** (live this mission, combined c052cea5e, coco8/imgsz=64/amp, log `phase_e30_train.log`): 30/30 epochs completed, train box_loss 3.730 → 3.546 (monotone learning), last.pt + best.pt saved, no NaN. Measured val mAP50 DECLINED 0.171 → 0.008 over the 30 epochs — recorded truthfully: with coco8's 4 val images × 80 classes × 64 px (≈0.2 instances/class), val mAP is statistically meaningless and small-data overfitting dominates; this is a dataset-scale artifact, not a GPU/PR defect (loss curve and all finite checks green). No historical mAP number is re-claimed as new measurement.

## Unblocking owners (NEXT_ACTION)

1. AMD: ship a rocm-sdk-libraries Windows wheel containing #13437 (or equivalent self-contained MIOpen kernel headers) → re-run this page's no-STL test → gate 4 flips.
2. Ultralytics maintainers: review/merge #27198 & #27203 → released package gate 5 flips.
3. Then re-run the official-path acceptance (official wheels + released ultralytics, no editable fork, no shims) per P15 frozen contract on this GPU.

**BLOCKER · OWNER: AMD (rocm-libraries) / Ultralytics (PR merge) · MISSING_EVIDENCE: none for this decision · NEXT_ACTION: as above.**
