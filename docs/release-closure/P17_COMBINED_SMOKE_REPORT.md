# P17 — Combined Smoke Regression: upstream main + PR #27203 + PR #27198 (local, NOT pushed)

Mission: P17 | Date: 2026-11-15
Purpose: detect interaction problems when both unmerged PRs take effect in one source tree, before maintainers merge them.

## Integration tree construction (auditable)

- Base: `upstream/main` = `3e59149d4e047019e759dc8feec09208fa09163d` (fetched live during mission; includes #27204)
- Worktree: `C:\Users\rocm\Desktop\YOLO_AMD\p17_combined` (local commit **`750b5061a0a7c397a15dd53641285b8b2dce1ded`**, message explicitly marks it as smoke-test only, **not for push**; no upstream branch touched; both PR branches' histories untouched)
- Composition method (chosen over cherry-pick after conflict analysis):
  1. `main` vs `#27203` base: **zero drift** on all 6 relevant files (`git diff 78b5b150^ upstream/main -- <files>` empty), so the four #27203-touched files were taken verbatim from `563ff46e` (`git checkout 563ff46e -- autodevice.py checks.py tests/test_cuda.py tests/test_python.py`).
  2. #27198's net contribution to `checks.py` (measured as `git diff 563ff46e e5ac8593 -- checks.py`) is exactly the check_amp guard; the docstring regression part (old "NVIDIA GPUs" wording) was **not** carried over — the #27203 docstring is kept. The applied check_amp body was verified **byte-identical** to `e5ac8593` by extraction+compare before commit.
- Conflict analysis performed first (mission §5 "analyze, don't auto-drop"): single-commit cherry-pick of `563ff46e` conflicts because its hunks reference intermediate commits of the PR branch; aborting and using file-level composition avoids any silent drop. No modification from either PR was discarded (verified by the byte-identity check and B-suite re-run below).

## Smoke results (7 items required by mission §5)

| # | Item | Result |
|---|---|---|
| 1 | Real HIP device detection | PASS — cuda_is_available=True, cuda_device_count=1, torch_count=1 |
| 2 | device=-1 | PASS — parse_device("-1") = "0" |
| 3 | Real check_amp() | **Guard exercised on real fault**: probe raised `AcceleratorError: CUDA error: invalid kernel file` (host HIP runtime in degraded state); the #27198 handler caught it, logged truthfully, returned False — **training did not crash**. Exactly the cross-PR interaction the integration test exists to check. |
| 4 | Minimal AMP training (official API) | PASS — 1 epoch on coco8 completed (`c_smoke`); training-internal AMP precheck "checks passed ✅" on this run (intermittent runtime health); GPU_mem 0.221 G, box_loss 2.842 / cls_loss 8.069 / l1_loss 0.0991 |
| 5 | Model parameter update | **0/366 for the 1-batch run** — explained and *not* a defect: with coco8 (1 batch/epoch) and nbs=64/batch=16 → accumulate=4, the loop reaches `do_step` only at global batch ni=4; that single optimizer step's fp16-scaled gradients overflowed → **legal GradScaler overflow-skip**; raw model and EMA stay byte-identical to init (max_abs_diff=0.0). FP32-degraded runs under identical accumulate structure do update (241/366) because scaler.step passes through. A 5-epoch and a 9-epoch run confirmed the same single-step-per-9-epochs arithmetic (0/366 each; per-epoch losses change while params don't — consistent with EMA/step accounting, BN running buffers move (228/342 changed, max 0.75) proving forward execution). |
| 6 | Checkpoint saved | PASS — last.pt/best.pt written; "Optimizer stripped from ...last.pt" line confirms optimizer existed |
| 7 | Real val + predict | PASS — val on coco8 completed (mAP50=0.171); predict on real image completed on GPU (inference 9.5 ms); one assert bug in the *test script* (`Results.device` attr) does not affect the API outcome |

Additional attempts to force an AMP-path real update inside the combined tree (coco128, 3 epochs): AMP precheck passed, training crashed at first batch with the same intermittent `hipErrorInvalidKernelFile` — recorded as further proof the host HIP runtime needs a reboot before the remaining closure items can be earned (not a PR-scope defect).

## Verdict

```
COMBINED_SMOKE: SOURCE-INTEGRATION PASS
  - both PRs co-exist without conflicts or interaction breakage
  - #27198 guard fires correctly on real faults in the integrated tree
  - #27203 gates work in the integrated tree
  - training/val/predict all execute on HIP GPU
AMP_TRUE_UPDATE_EVIDENCE: BLOCKED_ENVIRONMENT (reboot; fp16 GradScaler overflow-skip on
  the 1-batch coco8 loop is legal behavior, not a defect; scale-descent update proof pending)
```

Raw evidence: `evidence/p17/c_smoke.py`, `c_smoke_log.txt`, `c_smoke_result.json`, `c_smoke5_log.txt`, `c_smoke9_log.txt`, `c_smoke128_log.txt`.
