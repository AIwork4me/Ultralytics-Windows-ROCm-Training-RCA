# LONG RUN REPORT — G4.1 detection long training

Run: coco128 (public, official ultralytics dataset, 128 images) · YOLO26n · FP32 · 30 epochs planned · seed 42 · **third environment** (corrected 2026-11-14 audit): miniconda **base** env — python 3.13.13, ultralytics 8.4.174, torch 2.12.0+rocm7.14.0 official wheel (pre-fix MIOpen `74b4ee03`, host STL visible) — **NOT ENV A/B as previously labeled** · device=0, workers=2 · 2026-11-14 (env evidence: `g2_work/g4_console.log:2`; no in-process DLL probe was captured for this run — disclosed deviation)

## Outcome: **COMPLETED — 31 epochs (0–30), zero exceptions**

| Metric | Value |
|---|---|
| Epochs completed | 31/30 planned (0-indexed) |
| Wall time | 0.094 h (5.6 min) |
| Mean epoch time | 10.74 s (epoch 0 = 122.8 s incl. cold MIOpen compiles; steady-state 6.55–7.09 s, mean 7.00; isolated 12.3 s spike at epoch 20) |
| Fitness trajectory | 0.5050 (ep 0) → 0.6024 (ep 30), monotone-improving bands, **all finite** |
| Peak GPU memory | 4.69 GB |
| Exceptions / failed batches | 0 / 0 |
| Final checkpoint | valid (`runs/detect/g4_coco128_30ep/weights/last.pt`) |

Raw: `raw/g4_long_run_coco128.json` (per-epoch fitness/lr/epoch-time/GPU-mem, written incrementally), console `g2_work/g4_console.log`, results.csv under the run dir.

## What this establishes

- Long-run **stability**: 31 consecutive epochs on a public dataset with no NaN, no exceptions, no memory growth (4.69 GB flat), no failed/retried batches.
- **Learning**: fitness improves 0.505→0.602 with finite losses throughout — training is genuinely functional end-to-end (loss → backward → optimizer → val).

## Honest scope limits

- coco128 is a small public dataset: fitness 0.60 is a *functional* reference, **not** a model-quality benchmark (mAP on COCO-scale data was never claimed).
- Single machine, single family (gfx1151). Cross-machine quality comparison (Windows vs Linux ROCm) was **NOT_RUN — BLOCKED_HARDWARE** (no Linux GPU machine available).
- Epoch-time steady state (~7 s) was measured on the pre-fix official 7.14.0 wheel (third environment); per-epoch timings are recorded but no cross-version performance claim is derived from them here (see PERFORMANCE_REPORT for the matched FP32-vs-AMP A/B, same third environment). G4 was not run on ENV A/B — re-running it there with in-process DLL probes is a recorded pending item (`P8_INDEPENDENT_AUDIT.md`).
