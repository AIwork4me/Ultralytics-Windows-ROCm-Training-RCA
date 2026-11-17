# ISSUE DRAFT — ROCm/MIOpen: negative elapsed time in EvaluateInvokers destabilizes timing-based solver selection (Windows, gfx1151)

**Target repo**: `ROCm/MIOpen` (or rocm-libraries MIOpen) · **Status: DRAFT — Owner approval required before any upstream submission**
**Basis**: RCA repo `windows-training-validation/raw/g2_pose_main.log` (4 error lines, in-process DLL provenance `g2_pose_loaddll.json`), `amp-rca/ROOT_CAUSE.md` §3

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

Observed in multiple independent processes (`raw/g2_pose_main.log` — 4 lines; other YOLO
lifecycle logs). Note for honesty: the `envB_nostl_rep*.probe.log` files contain only
Info-level solver-evaluation lines, no error lines (earlier draft citations were wrong —
corrected in the 2026-11-14 audit, M3).
Consequence chain measured in this RCA: timing-based invoker evaluation feeds solver selection;
with corrupted timings the selected fp16 conv solver varies with cache/build state; fp16
inference coordinates shift 0.07–0.76 px between selections (no NaN, same detections/classes/confs),
which in turn flips Ultralytics' `check_amp` tolerance test → AMP silently disabled.
The shipping 7.14.1 wheel MIOpen (3.5.2.cd957402) **rarely emits this error** on the same
machine/workload: zero occurrences in clean runs, but one identical error line was observed
in an aborted run (in-repo `raw/scrambled_logs_20261114/g2_detect_envA_amptrack_main.log:150`)
— the faulty condition exists in both binaries. Official-wheel fp16 coordinate deltas vary
with cache state too (0.264 px fresh / 0.423 px default) but stay **below the 0.5 px
tolerance in both states** — what differs on the source-built binary is the delta magnitude
crossing the threshold.

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

- `windows-training-validation/raw/g2_pose_main.log` (error occurrences, lines 145–148)
- `windows-training-validation/raw/scrambled_logs_20261114/g2_detect_envA_amptrack_main.log` (official-wheel occurrence, line 150)
- `amp-rca/ROOT_CAUSE.md` (numeric consequence chain), `amp-rca/MINIMAL_REPRO.py`
