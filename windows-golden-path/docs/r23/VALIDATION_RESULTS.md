# VALIDATION_RESULTS.md (R23 draft — what is actually proven, 2026-11-15)

Machine: AMD Radeon RX 7900 XTX (gfx1100) · Windows 11 26300 · driver 32.0.21030.2001

## R21 harness validation (ENGINEERING_REFERENCE stack, physical GPU)

| Gate | Result | Evidence (repo path) |
|---|---|---|
| Binary provenance, fail-closed classification | ENGINEERING_REFERENCE (shim auto-detected; official DLL `e97891df…`, build `cd957402`, marker 0) | `evidence/raw/r21/r21A_provenance.json` |
| Torch/torchvision GPU gates (9) | **PASS 9/9** (incl. `torchvision.ops.nms`) | `evidence/raw/r21/r21A2_torch_gates.json` |
| no-STL regression, NO shim | **OFFICIAL_PRE_FIX_EXPECTED_FAIL** (exact #3956 signature, cold cache) | `evidence/raw/r21/r21D1_nostl_official.json` |
| no-STL regression, shim | **ENGINEERING_REFERENCE_PASS** | `evidence/raw/r21/r21D2_nostl_engref.json` |
| Exact CLI `yolo train model=yolo26n.pt data=coco8.yaml epochs=1 device=-1` | **PASS** exit 0 · GPU selected · AMP checks passed · epoch losses finite · val mAP50 0.943 · last/best.pt hashed | `evidence/raw/r21/r21E1_train_cli.json` |
| Real optimizer updates (supplementary harness) | **PASS** — 183 steps · 361/366 named-param tensors changed (max |Δ| 0.295) · GradScaler 8192→128 with 5 per-step backoffs · forward autocast 192/192 | `evidence/raw/r21/r21E2_optimizer.json` |
| Checkpoint interrupt → NEW-process resume → reload inference | see `r21E3_resume.json` (this gate raced fast epochs during bring-up; final verdict recorded there) | `evidence/raw/r21/r21E3_resume.json` |
| Stability (3 independent processes) | **PASS 3/3**, zero anomaly families | `evidence/raw/r21/r21F_stability.json` |

## R22 dev-channel candidate (official dev wheels, fix PROVEN in source)

Installed set: torch 2.15.0+gitf6cd88cb · rocm-sdk 10.3.0.dev0+ff576965
(TheRock ff576965 → rocm-libraries 4e7d93e3 → `f0a5d266` **behind_by=0**).

Gates A–G ran physically; per-gate verdicts live in `evidence/raw/r22-dev/`
and the aggregated report in `windows-golden-path/reports/r22-dev-candidate/`.
Ceiling: **DEV_CANDIDATE_PASS** — never OFFICIAL_STABLE.

## What is NOT proven (no claims made)

- No gfx1151 execution tonight (runner portable; run on 8060S unchanged)
- No CLEAN_WINDOWS_INSTALL (dev host → G9 BLOCKED_INFRASTRUCTURE)
- Full 10-run reliability matrix per arch (R21-scale subset run)
- Any STABLE-channel post-fix artifact (none exists — R22 BLOCKED_OFFICIAL_ARTIFACT)
- COCO8/coco128 mAP as model quality (smoke datasets only)
