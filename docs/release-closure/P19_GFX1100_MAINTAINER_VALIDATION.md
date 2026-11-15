# P19 — Maintainer-Requested Validation of PR #27203 @ d8fe65c8 (Windows gfx1100)

**Date:** 2026-11-15 · **Machine:** AMD Radeon RX 7900 XTX (gfx1100), Windows 11 build 26300, driver 32.0.21030.2001
**Stack:** Python 3.12.16 · torch 2.12.0+rocm7.14.1 (HIP 7.14.60850) · torchvision 0.27.0+rocm7.14.1 + `amd-torchvision-device-gfx1100`
**Runtime type:** ENGINEERING_REFERENCE — AMD wheel bytes unchanged; `HIPRTC_COMPILE_OPTIONS_APPEND` points at local freestanding-header shims (MIOpen fix not yet in official Windows wheels). Not official clean-install acceptance.

Maintainer request ([glenn-jocher, 2026-11-15T11:51Z](https://github.com/ultralytics/ultralytics/pull/27203#issuecomment-6893882839)): run two exact commands on real AMD hardware. Both were run against the live HEAD `d8fe65c8` (verified OPEN/MERGEABLE, unchanged after testing; diff = exactly `autodevice.py` + `checks.py`, +12/−12 vs `main`).

## Result 1 — `yolo train model=yolo26n.pt data=coco8.yaml epochs=1 device=-1`

**PASS — exit code 0.**

- `device=-1` auto-selected the real GPU through the PR's no-NVML fallback: `WARNING NVML stats unavailable, selecting the first CUDA devices without idle checks.` → `CUDA:0 (AMD Radeon RX 7900 XTX, 24560MiB)`
- AMP resolved `amp=True` (default), AMP checks **passed**
- Epoch 1/1 completed on GPU: box 0.8557 · cls 1.586 · l1 0.01287 (all finite)
- Validation completed: P 0.544 · R 0.965 · mAP50 0.943 · mAP50-95 0.687
- Checkpoints written: `last.pt` / `best.pt` (5.5 MB each; SHA256 in `phase_b_maintainer_train.json`)

Attempt 1 (exit 1) is archived too: `torchvision.ops.nms` raised `hipErrorInvalidDeviceFunction` because the venv lacked the `amd-torchvision-device-gfx1100` wheel — a known AMD split-wheel packaging dependency (P18), **not** a PR regression. Training epoch itself had completed before that crash. Installing the device wheel fixed it; the command was then rerun unchanged.

## Result 2 — `pytest tests/test_cuda.py`

**8 passed · 1 failed · 1 skipped — exit code 1** (387 s, pytest 9.2.0, 188 items collected, 10 executed after upstream conftest's default slow-filter).

- **8 passed:** `test_checks`, `test_amp`, `test_semantic_loss_all_ignore_amp[1]`, `[3]`, `test_train` (175 s, includes `compile=True` on ROCm), `test_track_exported_model[False]`, `[320]`, `test_autobatch`
- **1 failed:** `test_onnx_dynamic_spatial_outputs` — `assert 'CUDAExecutionProvider' in ['CPUExecutionProvider']`. PyPI `onnxruntime` has no ROCm CUDA-EP build for Windows; NVIDIA-only provider. The ONNX export itself succeeded on GPU, and the test **ran** (DEVICES=[0]) instead of skipping — which is the PR working. Not PR-scope.
- **1 skipped:** `test_train_cold_process_nonzero_device` — "requires an idle CUDA device with nonzero index" (single-GPU machine).

## A/B vs `main` (identical host, stack, dataset)

| measurement | main `3e59149d` | PR `d8fe65c8` |
|---|---|---|
| `torch.cuda.device_count()` | 1 | 1 |
| `cuda_device_count()` | **0** | **1** |
| `cuda_is_available()` | **False** | **True** |
| `select_idle_gpu(count=1)` | **[]** | **[0]** |
| `parse_device("-1")` | **"" → CPU** | **"0" → GPU** |
| test_cuda.py DEVICES | [] (all CUDA tests skip) | [0] (suite runs) |
| `test_checks` | would FAIL | PASS |

## No-NVML contract (fresh subprocess × CUDA_VISIBLE_DEVICES unset/0/empty/abc)

All PASS: `count=0`→`[]`; `count=1`→`[0]`; `count=2`→`[0]` (documented fewer-than-count); `indices=None`→`[0]`; `indices=[]`→`[]`; `indices=[0]`→`[0]`; documented warning emitted; GPU allocation succeeds on selection; no claim of verified idleness. (`evidence/raw/p19/phase_f_no_nvml_contract.json`)

## Optimizer-update evidence (supplementary harness, separate from the exact command)

The exact command trains a single batch (4 images) — by design not enough accumulation for an optimizer step, so real updates were earned separately (`epochs=8, batch=2, nbs=2, optimizer=SGD, lr0=0.01, device=0`): **11 `optimizer.step()` calls; 355/366 named-parameter tensors changed (max |Δ| 0.0199, all finite); GradScaler 65536→2048 (real fp16 overflow skips)**. Buffers excluded by design; no upstream source modified. v1 harness (auto AdamW, accumulate=32) correctly measured **no** updates and is archived as `phase_e_optimizer.log`.

## GO/NO-GO

- Gate 1 source+hardware: **PASS** (HEAD verified live before/after; import path = worktree; real gfx1100)
- Gate 2 train command: **PASS** (exact command, exit 0, GPU real, epoch+val+checkpoints)
- Gate 3 full test file: **FAIL_NONZERO_EXIT, diagnosed** — single NVIDIA-only onnxruntime failure; 8/9 executable tests pass; skip is single-GPU-environmental
- Gate 4 contribution quality: **PASS** (minimal 2-file diff preserved; CI green at HEAD incl. windows-latest; no PR changes made)
- Gate 5 upstream communication: draft prepared (posted only after user approval)

**Overall: READY_TO_REPORT_TO_MAINTAINER.** Hardware evidence supports merging the device-detection change; the one test failure is an onnxruntime provider limitation unrelated to the PR.

## Raw evidence

`evidence/raw/p19/` (24 files + `SHA256SUMS.txt`; manifest 111 entries): `environment.json`, `runtime_provenance.json`, `phase_b_maintainer_train.{log,json}`, `phase_b_maintainer_train_attempt1.log`, `phase_c_full_test_cuda.{log,json}`, `baseline_vs_pr.json`, `phase_f_no_nvml_contract.{log,json}`, `phase_e2_optimizer_evidence.json`, frozen inputs (`pr27203_d8fe65c.diff`, `test_cuda.py.frozen`, `AGENTS_md.frozen`), `ci_status_frozen_head.log`. Reproduction scripts: `scripts/p19/`.
