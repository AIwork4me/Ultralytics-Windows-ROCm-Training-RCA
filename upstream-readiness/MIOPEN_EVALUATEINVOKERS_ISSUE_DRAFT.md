# ISSUE DRAFT — ROCm/MIOpen: negative elapsed time in EvaluateInvokers destabilizes timing-based solver selection (Windows, gfx1151)

**Target repo**: `ROCm/MIOpen` (or rocm-libraries MIOpen) · **Status: DRAFT — Owner approval required before any upstream submission**
**Basis**: RCA repo `windows-training-validation/raw/envB_nostl_rep*.log`, `amp-rca/ROOT_CAUSE.md` §3

## Environment

- Windows 11 build 26200, Ryzen AI MAX+ 395 (Strix Halo), Radeon 8060S, **gfx1151**
- Driver 32.0.22032.6002; HIP 7.14.60850
- MIOpen built from rocm-libraries @ f0a5d266 (post PR #13437 merge; MIOpen 3.6.2.f0a5d266), MIOPEN_BACKEND=HIP, MIOPEN_USE_COMGR=ON, clang from the 7.14.1 wheel SDK
- Reproduction context: PyTorch 2.12.0+rocm7.14.1 wheel driving convolutions (YOLO26n); errors logged to stderr at default level

## Symptom

During normal operation, MIOpen repeatedly logs:

```
MIOpen: Error [EvaluateInvokers] DESKTOP-...:C:/w58m/projects/miopen/src/conv/solver_finders.cpp:535:
Invalid elapsed time detected in EvaluateInvokers, failed condition: elapsed <= 0
```

Observed in multiple independent processes (`envB_nostl_rep1/2/3.probe.log`, YOLO detect run logs).
Consequence chain measured in this RCA: timing-based invoker evaluation feeds solver selection;
with corrupted timings the selected fp16 conv solver varies with cache/build state; fp16
inference coordinates shift 0.2–0.8 px between selections (no NaN, same detections/classes/confs),
which in turn flips Ultralytics' `check_amp` tolerance test → AMP silently disabled.
The shipping 7.14.1 wheel MIOpen (3.5.2.cd957402) does **not** emit this error on the same
machine/workload and keeps fp16 coordinate deltas ≤ ~0.23 px.

## Reproduction sketch

1. Build MIOpen from rocm-libraries develop (3.6.2) for Windows HIP, per the validated Phase-5.8 recipe.
2. Drive a YOLO26n detect train/inference (Conv2d-dominant workload) on gfx1151.
3. Observe the EvaluateInvokers error lines during solver evaluation.
4. Cross-check fp16-vs-fp32 coordinate deltas before/after a fresh MIOpen cache
   (`MIOPEN_USER_DB_PATH`/USERPROFILE redirect) — the selected kernel and the delta change.

## Ask

- Confirm whether negative elapsed values are a known Windows HIP event-timing issue (hipEvent elapsed_time returning negative under this driver) or an internal timing computation bug in the invoker evaluator.
- Guidance: should `elapsed <= 0` invokers be excluded from selection rather than logged-and-kept?
- Happy to provide full raw logs, the source-built DLL provenance (sha256 `ed7c67a9…` @ f0a5d266), and a minimal repro script.

## Related local artifacts (evidence-first RCA repo)

- `windows-training-validation/raw/envB_nostl_rep*.log` (error occurrences)
- `amp-rca/ROOT_CAUSE.md` (numeric consequence chain), `amp-rca/MINIMAL_REPRO.py`
