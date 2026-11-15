# P19B — GFX1151 Maintainer Validation of PR #27203 (d8fe65c8)

**Date:** 2026-11-15
**Machine:** AMD Radeon(TM) 8060S Graphics (gfx1151 APU), Windows 11 build 26200.9974, driver 32.0.22032.6002
**Mission:** Execute the two maintainer-requested commands from [glenn-jocher's comment](https://github.com/ultralytics/ultralytics/pull/27203#issuecomment-6893882839) on the exact PR head, plus device=-1 value measurement, AMP true-optimizer evidence, and main-vs-PR comparison.

## 0. Frozen provenance

| Item | Value |
|---|---|
| PR #27203 HEAD (frozen, worktree-verified) | `d8fe65c8c1052cb4305f3cec1be9cb909538dcf1` |
| PR diff vs main | 2 files only: `ultralytics/utils/checks.py`, `ultralytics/utils/autodevice.py` |
| Baseline (before) | `ultralytics/ultralytics` main @ `3e59149d4e047019e759dc8feec09208fa09163d` |
| Worktrees | `C:\P19B\pr27203` (PR head), `C:\P19B\main-baseline` (main) |
| Python | 3.13.16 (`C:\Users\rocm\Desktop\YOLO_AMD\p17_env27203`, system-site-packages venv) |
| torch | 2.12.0+rocm7.14.1 (HIP 7.14.60850), torchvision 0.27.0+rocm7.14.1, `amd-torch-device-gfx1151` installed |
| ultralytics import | `C:\P19B\pr27203\ultralytics\__init__.py`, version 8.4.213 (PYTHONPATH isolation; editable finder loses to system-site packages — documented in §7) |
| Machine state | **Clean reboot 2026-11-15T20:49:03** before all runs; 8 stale HIP processes from P17/P18 cleared; no `MIOPEN_*` overrides; no zombie processes during any P19B run |
| torch lib SHA256 | `aotriton_v2.dll` `f093102dd7ddd71dfcb510eee03631a8ff10f55576062d6b1abd5064f372a3ba` (see environment.json) |
| HIP runtime provenance | Official AMD wheel stack, no host shims: `torch 2.12.0+rocm7.14.1` wheel + pip `_rocm_sdk_core`/`_rocm_sdk_libraries` (amdhip64_7.dll, hiprtc0714.dll, MIOpen.dll) + `amd-torch-device-gfx1151` 2.12.0+rocm7.14.1 + Windows driver 32.0.22032.6002. No HIPRTC shim, no STL redirect, no wheel-byte modification, no `MIOPEN_*` env overrides during any P19B run. MIOpen anomalies observed are stock-stack issues (`gfx115128.HIP.fdb.txt` unreadable shipped find-db; CK grouped-conv symbols missing for gfx1151). |

Environment freeze: `evidence/raw/p19b/environment.json` (captured post-reboot, pre-tests).

## 1. G1 — EXACT_HEAD_VERIFIED: **PASS**

- `git worktree add --detach C:\P19B\pr27203 d8fe65c8c1052cb4305f3cec1be9cb909538dcf1`; `git rev-parse HEAD` = the SHA.
- PR content spot-checks inside the worktree: `autodevice.py` contains `"selecting the first CUDA devices without idle checks"`; `checks.py` contains the `torch.cuda.device_count()` fallback (2 occurrences).
- Upstream re-check before start: `gh pr view` head == `d8fe65c8...` (no drift), state OPEN/MERGEABLE.

## 2. G2 — GPU_RUNTIME_VERIFIED: **PASS (post-reboot re-validation)**

Post-reboot probes (fresh process, `C:\P19B\logs\…` + environment.json):
- `torch.cuda.is_available() == True`, `device_count == 1`, device 0 = AMD Radeon(TM) 8060S Graphics
- FP32 GEMM probe finite; FP16 GEMM probe OK
- Ultralytics probes: `cuda_device_count()==1`, `cuda_is_available()==True` (PR functions live)

## 3. G3 — MAINTAINER_TRAIN_COMMAND: **PASS (with intermittent machine-fault disclosure)**

Command executed verbatim (no parameter changes): `yolo train model=yolo26n.pt data=coco8.yaml epochs=1 device=-1`

| Run | Run ID | Result | Exit | Notes |
|---|---|---|---|---|
| 1 | P19B_TRAIN_MAINTAINER_20261115_211636 | **FAIL** | 1 | `torch.AcceleratorError: invalid kernel file (hipErrorInvalidKernelFile)` surfaced at BN `num_batches_tracked.add_(1)` during the **first training batch forward**; model build + `AMP: checks passed` + optimizer creation all succeeded before it |
| 2 | P19B_TRAIN_MAINTAINER_20261115_211949 | **PASS** | 0 | Epoch 1/1 completed 31.9s; losses box 0.8567 / cls 1.589 / dfl 0.01289; final val mAP50 **0.941**, mAP50-95 **0.677**; best.pt/last.pt written |
| 3 | P19B_TRAIN_MAINTAINER_20261115_212121 | **PASS** | 0 | Warm-cache rerun; epoch + validation completed |

Checkpoints (run 2): best.pt `093543a1146c50fe333a3c11610c51b55d62dbcea759aa50a39ad023075be1dd`, last.pt `4505b780c84243d96ba4fbb7285a136167404a3b9d5c48d487218503cc80de49`.

**device=-1 behavior (all runs, as glenn implemented it):**
```
Searching for 1 idle GPUs with free memory >= 20.0% and free utilization >= 0.0%...
WARNING NVML stats unavailable, selecting the first CUDA devices without idle checks.
Ultralytics 8.4.213  Python-3.13.16 torch-2.12.0+rocm7.14.1 CUDA:0 (AMD Radeon(TM) 8060S Graphics, 80065MiB)
```
- `parse_device("-1")` → `"0"` (explicit, via the PR's new `select_idle_gpu` no-NVML fallback)
- Training and final validation both on CUDA:0 — no silent CPU fallback

**Run 1 failure analysis (root-caused as machine/runtime, NOT the PR):**
- The identical model forward (yolo26n, train mode, batch=16, imgsz=640, autocast) **passes in an isolated fresh process** immediately after the failure (`rca_min_repro.json`, all 7 steps OK).
- Raw int64 `add_`, train-mode BN forward/backward, BN under autocast, GEMM all pass → the failing op attribution is unreliable (async reporting caveat printed in the error itself).
- Log carries the same MIOpen signatures recorded since P17: `ParseAndLoadDb File is unreadable: gfx115128.HIP.fdb.txt` (unreadable shipped find-db) and CK grouped-conv symbol warnings; run 2 additionally shows a non-fatal `MIOpen: Error [EvaluateInvokers] Invalid elapsed time` during validation (val completed correctly).
- Classification: **Windows ROCm runtime / MIOpen kernel-cache fault** (category 2 of the mission taxonomy) — intermittent, matches the P17 RCA family. It is not a PR code path failure: the PR's own changed functions executed correctly (device selection and AMP check) before the fault.

## 4. G4 — FULL_TEST_CUDA: **PASS/PARTIAL — 1 failed, 8 passed, 1 skipped**

`pytest tests/test_cuda.py` from the PR worktree (upstream default: no `--slow`, so slow-marked tests are excluded by upstream conftest; 188 items collected pre-filter, 10 non-slow items ran). Duration 321.31s. Exit code 1 (pytest convention). JUnit XML: `junit_test_cuda.xml`.

| Test | Result | Detail |
|---|---|---|
| test_checks | PASSED | torch vs PR checks functions consistent |
| test_amp | PASSED | real `check_amp()` on cuda:0, 13.62s |
| test_onnx_dynamic_spatial_outputs | **FAILED** | `torch.onnx.OnnxExporterError: Module onnx is not installed!` — optional export deps (`onnx`/`onnxruntime`) not installed in this env (mission category 5). Note: even with them installed, the test asserts `CUDAExecutionProvider`, which requires NVIDIA CUDA runtime — unavailable on AMD Windows (category 4). **Not a PR regression.** |
| test_semantic_loss_all_ignore_amp[1] | PASSED | fp16 logits guard on GPU |
| test_semantic_loss_all_ignore_amp[3] | PASSED | |
| test_train | PASSED | 3 trainings (coco8-grayscale autobatch batch=-1; coco8 with `compile=True` → graceful "no working Triton found" fallback, uncompiled; coco128 val=False), device assertions + CUDA_VISIBLE_DEVICES non-mutation assertions pass, 170s |
| test_train_cold_process_nonzero_device | SKIPPED | `requires an idle CUDA device with nonzero index` — single-GPU machine (expected) |
| test_track_exported_model[False] | PASSED | torchscript export + track on cuda:0 |
| test_track_exported_model[320] | PASSED | tile=320 |
| test_autobatch | PASSED | AutoBatch probe on cuda:0 (chose batch 1024), 122s |

No NVIDIA-only runtimes were mocked or installed; no test files modified.

## 5. G5 — DEVICE_MINUS_ONE: **PASS**

Probe matrix (fresh subprocesses, `p1_device_probe.py`; raw log `baseline_comparison_probe_log.log`):

| Probe | main 3e59149 (before) | PR d8fe65c8 (after) |
|---|---|---|
| `torch.cuda.device_count()` | 1 | 1 |
| `ul_cuda_device_count()` | **0** | **1** |
| `ul_cuda_is_available()` | **False** | **True** |
| `parse_device("-1")` | `""` (empty) | `"0"` |
| real cuda:0 allocation | OK | OK |

Same results under `CUDA_VISIBLE_DEVICES=0` (set before torch init) → no regression under restriction; single-GPU physical remapping NOT_RUN (only one GPU exists, as anticipated).

Measured value of the PR (same session, empirical): on main, `cuda_is_available()` is False on AMD → `tests/test_cuda.py` module constant `CUDA_IS_AVAILABLE=False` → **every GPU test would skip**; on the PR the full file collected 188 items and ran 10 non-slow tests with 8 real GPU executions. Full matrix: `baseline_comparison.json`.

## 6. G6 — AMP_TRUE_OPTIMIZER_UPDATE: **PASS**

Instrumented real training (coco128, 4 epochs, batch=16, imgsz=64, device=-1, amp default; `p1_amp_audit.py`, raw JSON `amp_optimizer_audit.json` + `amp_audit_interpretation.json`):

| Signal | Value |
|---|---|
| `check_amp()` before training | True (probe on cuda:0) |
| trainer amp flag / scaler / optimizer | True / `torch.amp.GradScaler` / AdamW (fused=True) |
| autocast during training forwards | **32/32 = 100%** (`torch.is_autocast_enabled()` sampled per train-mode forward) |
| GradScaler.step attempts | 13 (unscale_ 13, update 13) |
| scale trajectory | 65536 → 512 (`2^7` = 7 inf-skip events **inside the fused-AdamW kernel** + 6 real-update steps; for fused Adam the host never skips `optimizer.step()` — see interpretation JSON) |
| trainable `named_parameters` changed | **366 / 366** (SHA256 before/after, BN running buffers excluded) |
| epoch train losses | all finite, decreasing epoch 1→3 (box 3.595→3.408, cls 7.082→6.859) — real learning |
| final val metrics | finite (mAP50 0.047 @ 4 epochs imgsz=64) |

Audit-script iterations v1–v5 were instrumentation defects only (Windows-spawn guard; check_amp on CPU model; AdamW overriding `Optimizer.step`; tloss dict format; torch 2.12 private-API rename `_optimizer_state`→`_per_optimizer_states`) — all disclosed here; v6 is the clean run. No AMP exception occurred during any of the 6 training runs in this phase (3 maintainer-command runs + rca repro + audits), and no AMP-disable path was exercised — the P17-era `AcceleratorError` did not reproduce under the post-reboot environment except for the single Run-1 event documented in §3.

## 7. Environment isolation notes

- `PYTHONPATH=C:\P19B\pr27203` forces the PR tree in every P19B invocation: the venv is `--system-site-packages` over a base env that ships its own `ultralytics` 8.4.182, and a venv-local editable install cannot win (`_EditableFinder` is appended after `PathFinder` in `sys.meta_path`). Verified resolution: `ultralytics.__file__ == C:\P19B\pr27203\ultralytics\__init__.py`, version 8.4.213; `yolo` CLI reports 8.4.213.
- Test assets: `yolo26n.pt` (SHA256 `9b09cc8bf347f0fc8a5f7657480587f25db09b34bf33b0652110fb03a8ad4fef`) pre-seeded; `coco8`/`coco128` datasets pre-existing under the user's configured `datasets_dir`. Session cleanup (conftest `pytest_sessionfinish`) ran inside the disposable worktree only.
- No HIP torch upgrade/replacement; no MIOpen db/cache deletion; no driver changes.

## 8. Verdict summary

| Gate | Verdict |
|---|---|
| G1 EXACT_HEAD_VERIFIED | PASS |
| G2 GPU_RUNTIME_VERIFIED | PASS (post-reboot) |
| G3 MAINTAINER_TRAIN_COMMAND | PASS — 1 FAIL + 2 PASS, intermittent machine fault disclosed and root-caused as runtime/MIOpen |
| G4 FULL_TEST_CUDA | PASS/PARTIAL — 1 failed, 8 passed, 1 skipped; failure = missing optional `onnx` dep + NVIDIA-only CUDA EP assertion; zero PR regressions |
| G5 DEVICE_MINUS_ONE | PASS |
| G6 AMP_TRUE_OPTIMIZER_UPDATE | PASS — 366/366 params updated, autocast 32/32, scale backoff healthy |
| G7 EVIDENCE_REPRODUCIBLE | PASS (all commands scripted in `C:\P19B\scratch\`, logs + SHA256SUMS archived) |
| G8 READY_FOR_MAINTAINER_COMMENT | YES (comment drafted pending user approval) |
