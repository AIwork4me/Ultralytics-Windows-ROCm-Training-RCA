# P15.9 — Continuous GPU CI and Release Regression (2026-11-15)

Status: Layer A partially delivered upstream; Layer B **BLOCKED_RUNNER** (maintained) with a complete reproducible local-runner contract.

## Layer A — ordinary upstream CI

Delivered in P15 (in open PRs; not yet merged):

1. **PR [#27198](https://github.com/ultralytics/ultralytics/pull/27198)** `fc72b4e`: `check_amp` probe-exception guard retained by 2 minimal CPU-runnable regression tests (probe failure → degrade-to-FP32 + log; KeyboardInterrupt propagates). These run on every ordinary CI target, including GPU-less runners — closing the regression that #26967 introduced silently.
2. **PR [#27203](https://github.com/ultralytics/ultralytics/pull/27203)**: makes the CUDA-generic test gates (`cuda_device_count` without nvidia-smi, `GPUInfo.select_idle_gpu` without NVML) actually run on AMD HIP hosts. Verified on gfx1151: `tests/test_cuda.py::test_amp` SKIPPED → **PASSED**. This is the prerequisite for upstream AMD GPU CI to execute at all instead of silently skipping (the skip-all behavior was verified today on upstream `main` @ `d0cfcea`).

Existing Layer A (unchanged): Ruff, compatibility tests, docs validation, `tests/test_rocm.py` (MIGraphX export matrix, HIP-gated) already in upstream `main`.

## Layer B — physical Windows Radeon GPU CI

Required classes: gfx1151 + a second distinct supported class. Status: **BLOCKED_RUNNER** — no self-hosted GPU runner is provisioned (owner decision, hardware/cost/security responsibility). No mandatory skip is counted as PASS.

### Reproducible local-runner contract (produces identical artifacts)

Any Windows machine with the supported Radeon GPU can execute the equivalent of the CI job by running, in order (each leg a fresh process, official released stack only):

```powershell
# 0) one-time: official driver + official wheels + released ultralytics (golden-path/WINDOWS_SETUP.md)
python golden-path/verify_environment.py --out env.json                 # identity + in-process DLL hash
python scripts/p15/p15_run.py amp-probe                                 # autocast + GradScaler + update truth
python scripts/p15/p15_run.py smoke --workers 0                         # reliability: w0
python scripts/p15/p15_run.py smoke --workers 2                         # reliability: w2
python scripts/p15/p15_run.py smoke --workers 4                         # reliability: w4
python scripts/p15/p15_run.py smoke --workers 2 --warm                  # reliability: warm cache
python scripts/p15/p15_run.py train30                                   # representative 30 epochs
# (interrupt after epoch >= 20: Stop-Process -Force on the training PID)
python scripts/p15/p15_run.py resume --run-id p15_30ep_w2               # new-process resume
python scripts/p15/p15_run.py finalcheck --run-id p15_30ep_w2           # val + reload + inference
```

Artifacts: one JSON per leg under `release-provenance/raw/p15_gfx1151/` (schema = the P15 driver's fields: env identity, AMP verdicts, GradScaler step table, wall times, row counts, SHA256 of results.csv/weights). A CI runner is simply this sequence under automation with the JSONs uploaded; the local contract and a hosted runner MUST produce byte-comparable schemas.

### Security rules (for the future runner)

- No privileged execution of untrusted fork code; PR-triggered GPU jobs run only allowlisted RCA scripts on controlled trusted runners.
- No repository secrets on GPU jobs.
- No unrestricted persistence across PRs (fresh workspace per job).
- No skip-to-green: a missing runner ⇒ BLOCKED_RUNNER, never a green check.

## Layer C — release regression

The same leg sequence (against the NEW official wheel) is the release-acceptance regression for any future AMD Windows wheel: it re-verdicts GATE 3 automatically from the recorded criteria (marker count, no-STL control, training/AMP/checkpoint legs).

## Required verdict

- Layer A: **IN_PROGRESS** (two open PRs carry the minimal regression protection).
- Layer B: **BLOCKED_RUNNER** — manual real-GPU tests (P14/P15) are valuable evidence but are not an operational CI service.
