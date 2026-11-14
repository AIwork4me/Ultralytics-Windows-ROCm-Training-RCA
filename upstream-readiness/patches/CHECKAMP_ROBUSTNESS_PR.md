# PR draft — ultralytics: check_amp must not let a probe exception crash training (regression vs 8.4.182)

**Target**: ultralytics/ultralytics · **Status: READY — live repro captured; patch + regression test prepared**

## Problem

PR #26967 (8.4.197) redesigned `check_amp` (per-layer relative-norm check, no weights download — a big improvement) but **also removed the exception handling** the old probe had. 8.4.182's `check_amp` wrapped the probe in `try/except (ConnectionError | AttributeError, ModuleNotFoundError | AssertionError)` → any probe failure disabled AMP with a warning and **training continued in FP32**. The new `check_amp` lets **any** exception propagate into `BaseTrainer._setup_train`, so a probe-time backend error now **crashes the user's training run** instead of disabling AMP.

## Live reproduction (Windows ROCm, gfx1151)

Environment: Radeon 8060S (gfx1151 iGPU), Windows 11 build 26200, torch 2.12.0+rocm7.14.1 (official AMD wheel), ultralytics 8.4.212 (this PR's code via PYTHONPATH), MIOpen 3.6.2 source-built (f0a5d266) hybrid — a state where MIOpen's kernel fingerprint DB is unreadable:

```
MIOpen: Warning [ParseAndLoadDb] File is unreadable: "..._rocm_sdk_libraries\bin\gfx115128.HIP.fdb.txt"
...
torch.AcceleratorError: CUDA error: invalid kernel file
Search for 'hipErrorInvalidKernelFile' ...
  File ".../ultralytics/utils/checks.py", line 1079, in check_amp
      m(torch.rand(8, 3, 256, 256, device=device))  # batch 8, ...
  File ".../ultralytics/utils/checks.py", line 1069, in compare_amp
      y = layer.forward(inputs[0])  # forward() skips this layer's own hook
```

On 8.4.182 the same class of failure produced "checks failed … AMP will be disabled during training" and the run continued. On 8.4.197+ it aborts `trainer.train()`. (Underlying MIOpen env-integrity issue is tracked separately; the point here is Ultralytics' resilience contract: **the AMP probe must degrade gracefully, never take the training run down.**)

## Fix (minimal — restore the 8.4.182 resilience contract for the new probe)

```python
    close = []  # per-layer agreement of AMP with FP32
    ...
-   with torch.no_grad():
-       m(torch.rand(8, 3, 256, 256, device=device))  # batch 8, as GTX 16xx AMP faults appeared only at batch >= 7
-   if all(close):
+   try:
+       with torch.no_grad():
+           m(torch.rand(8, 3, 256, 256, device=device))  # batch 8, as GTX 16xx AMP faults appeared only at batch >= 7
+   except Exception as e:
+       LOGGER.error(
+           f"{prefix}checks failed with an exception ({type(e).__name__}: {e}). Anomalies were detected with "
+           f"AMP on your system that may lead to NaN losses or zero-mAP results, so AMP will be disabled during training."
+       )
+       return False
+   if all(close):
```

(A `except Exception` is deliberate: probe-time GPU errors are heterogeneous across backends — HIP/CUDA/MPS — and the function's contract is a boolean verdict, not an error surface. `KeyboardInterrupt`/`SystemExit` still propagate.)

## Regression test (CPU-runnable, no GPU)

`tests/test_check_amp_probe_exception.py`: monkeypatch `torch.nn.Module.forward` for the probe model to raise `RuntimeError` once, call `check_amp(model.cpu())`-equivalent via the internal probe path, assert it returns False and logs, and does NOT raise. (GPU paths exercised by the hardware matrix where available.)

## Validation performed

- Live repro before fix: `AcceleratorError` propagates (stderr archived in the evidence repo).
- After fix (local apply): probe exception → `LOGGER.error` + `return False` → trainer continues with `amp=False` (verified by running the trainer setup path on the same env).
