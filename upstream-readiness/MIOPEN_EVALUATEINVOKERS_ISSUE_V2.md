# Issue draft — MIOpen EvaluateInvokers "Invalid elapsed time detected (elapsed <= 0)" on gfx1151: rare intermittent error under full training load, not reproducible in isolation

**Target**: ROCm/rocm-libraries (MIOpen component) · **Status: READY — RCA marked UNRESOLVED per mission §4.3 (cannot reproduce sufficiently → submit precise evidence, do not guess)**

## Summary

During sustained Ultralytics YOLO training on Windows ROCm (gfx1151, Radeon 8060S, ROCm 7.14.x PyTorch wheels), MIOpen intermittently logs:

```
MIOpen: Error [EvaluateInvokers] Invalid elapsed time detected. Using 0 as elapsed time.
failed condition: elapsed <= 0
solver_finders.cpp:535
```

Training continues (the error is non-fatal), but it indicates the solver benchmarking timer returned a non-positive elapsed time — worth investigating because timing validity underpins solver selection.

## Occurrences (all in real training contexts)

| Context | Environment (in-process DLL SHA256) | Count | Evidence |
|---|---|---|---|
| Ultralytics pose lifecycle, MIOpen 3.6.2 source-built from PR #13437 merge | MIOpen `ed7c67a9…` (in-process probe) | 4× | repo log `windows-training-validation/raw/g2_pose_main.log` lines 145–148 |
| Ultralytics detect AMP-track attempt (aborted), official MIOpen 3.5.2 | binary not probe-verified for that attempt | 1× | `raw/scrambled_logs_20261114/g2_detect_envA_amptrack_main.log:150` |
| Clean official-wheel re-run of the same lifecycle | `e97891df…` (in-process probe) | 0× | `raw/g2_detect_envA_amptrack_rerun_*.log` |
| envB no-STL probe logs | — | 0× | `raw/envB_*_probe.log` |

## Isolation attempt (negative result — cannot reproduce without Ultralytics)

A dedicated minimal reproducer (`windows-training-validation/tests/g3_evaluateinvokers_repro.py`, pure `torch.nn.Conv2d(+BatchNorm2d)` forward+backward, **no Ultralytics**) ran 9 conv configurations × fp16/fp32 × fresh-cache Find-1 path (fresh `MIOPEN_USER_DB_PATH`/`HOME` per probe, subprocess-isolated so every stderr line is attributable) on **both** the official MIOpen 3.5.2 wheel and the source-built 3.6.2: **0 occurrences in 18 probes** (`raw/g3_evi_ENV_A_official.json`, `raw/g3_evi_ENV_B_patched.json`; repeat pair deterministic). Configs ranged 3→64 channels, k3/k5, stride 1/2, batch 4–16, hw 32–128.

## Interpretation (honest scope)

- The trigger requires the **full training load context** (hundreds of distinct conv shapes queried in sequence, warm cache evolution, dataloader/HIP-stream timing under load) — not any single shape in isolation.
- It is **rare and intermittent** (4 log lines across multi-hour sessions), on both stock and patched MIOpen, both cache states.
- We are **not** claiming a root cause: candidates range from HIP event-timing granularity to solver-benchmark scheduling races, but our data cannot discriminate. Marking RCA **UNRESOLVED** and handing the evidence to maintainers.

## Ask

1. Whether `elapsed <= 0` in `solver_finders.cpp:535` is a known artifact of a specific timer/solver path on RDNA3 iGPU (gfx1151) / Windows HIP.
2. Pointers to the timer origin would let us build a discriminating experiment (we can run instrumented builds on this hardware).
3. If confirmed benign (e.g., timer wraparound guard), consider downgrading the log severity so real errors stay visible.

## Reproduction pointers

- Hardware: AMD Ryzen AI MAX+ 395 (Strix Halo), Radeon 8060S, gfx1151, Windows 11 build 26200, driver 32.0.22032.6002
- Stack: torch 2.12.0+rocm7.14.1 (official AMD wheel), HIP 7.14.60850, MIOpen 3.5.2 (official) / 3.6.2+f0a5d266 (source-built)
- The full training-context reproduction is "run the Ultralytics lifecycle harness repeatedly on this hardware" (commands in the linked repo); the isolation-negative reproducer is in the same repo.

*Evidence repository: AIwork4me/Ultralytics-Windows-ROCm-Training-RCA (all paths above are in-repo raw logs/JSONs with in-process DLL SHA256 provenance).*
