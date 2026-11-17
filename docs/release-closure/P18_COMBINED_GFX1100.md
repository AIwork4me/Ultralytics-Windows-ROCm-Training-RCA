# P18 — Combined (PR #27198 + #27203) GFX1100 Integration

**Base**: upstream `main` @ `3e59149d4e047019e759dc8feec09208fa09163d` · **Local temp merge head**: `c052cea5e` (NOT pushed anywhere; both PR histories preserved via `--no-ff` merges, zero conflicts) · **Machine JSON**: `evidence/raw/p18/p18_combined_results.json`

## D1–D8 — PASS (script `phase_d_combined.py`, exit 0)

| # | Check | Result |
|---|---|---|
| D1 | Radeon detection via both PR paths | torch=checks counts agree (1), name OK |
| D2 | `device=-1` auto-select | `parse_device("-1")="0"`, `select_idle_gpu(0.2)=[0]` |
| D3 | real `check_amp` | **True** (AMP: checks passed) |
| D4 | real AMP train (1 epoch coco8 64px) | last.pt + best.pt saved |
| D5 | real parameter update | 594 tensors, max\|Δw\|=0.734 |
| D6 | checkpoint reload | task=detect, nc=80, weights round-trip |
| D7 | validation of trained ckpt | mAP50=0.171, mAP50-95=0.052 (GPU) |
| D8 | inference | bus.jpg @320px → **5 boxes on cuda:0**, conf 0.83/0.82/0.76/0.55 |

[log: `phase_d_combined.log`]

## D9 — Real interruption + resume in a NEW process — PASS (script `phase_d9_resume.py`, exit 0)

1. Subprocess A trains 6 epochs (coco8, amp=True); driver polls for first `last.pt`
2. At **epoch 3** (mid-run, process alive) A is hard-killed (returncode 1)
3. Interrupted checkpoint carries `optimizer` state, `train_args` (epochs=6), best_fitness
4. Subprocess B (fresh interpreter): `YOLO(last.pt).train(resume=True)` → completes to **final_epoch 5** (=epochs-1), results.csv has all rows, exit 0

This is a true process-death resume (not a weights-reload), restoring optimizer/epoch. [log: `phase_d9_resume.log`]

Regression captures across D: no device-numbering errors, no wrongly-skipped GPU tests (C8), no probe degradation (D3 True), RuntimeError guard intact (B2 on #27198 tree), no training crash, checkpoint recovery works (D6/D9).

## Phase F — Windows stability — 7/7 PASS (script `phase_f_stability.py`, exit 0)

| Stage | amp fwd/bwd | ckpt saved | reload+predict | rc | time |
|---|---|---|---|---|---|
| cold0 / cold1 / cold2 (fresh processes) | ✅ | ✅ | ✅ | 0 | ~14–19 s |
| warm (2 trainings, 1 process) | ✅ | ✅ | ✅ | 0 | — |
| workers=0 / 2 / 4 | ✅ | ✅ | ✅ | 0 | ~17–19 s |

Windows DataLoader multiprocessing (workers 2/4) works; repeated cold/warm starts stable; GPU memory returns to baseline between process runs (allocator cache retention ≈0.5 GB in-process is expected). No HIP teardown deadlocks, no DLL-lock failures, no driver events. Classification: no SOURCE_REGRESSION / ROCM_RUNTIME_FAILURE / WINDOWS_DRIVER_ISSUE observed on the shim-enabled ENGINEERING_REFERENCE stack. [log: `phase_f_stability.log`]

## Verdict

**COMBINED GFX1100 SMOKE VALIDATION: PASS** (temp integration, NOT merged upstream, NOT claimed as an upstream-main state).
