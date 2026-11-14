# LONG RUN REPORT — G4.1 detection long training

Run: coco128 (public, official ultralytics dataset, 128 images) · YOLO26n · FP32 · 30 epochs planned · seed 42 · ENV B (source-built patched MIOpen `ed7c67a9…`) · device=0, workers=2 · 2026-11-14

## Outcome: **COMPLETED — 31 epochs (0–30), zero exceptions**

| Metric | Value |
|---|---|
| Epochs completed | 31/30 planned (0-indexed) |
| Wall time | 0.094 h (5.6 min) |
| Mean epoch time | 10.74 s (epoch 0 = 122.8 s incl. cold MIOpen compiles; steady-state ~6.8–6.9 s) |
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
- Epoch-time steady state (~6.8 s) includes the EvaluateInvokers-anomalous source-built MIOpen (ENV B); per-epoch timings are recorded but no cross-version performance claim is derived from them here (see PERFORMANCE_REPORT for the matched FP32-vs-AMP A/B on the official wheel).
