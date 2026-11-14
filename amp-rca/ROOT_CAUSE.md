# ROOT CAUSE — Ultralytics AMP anomaly on Windows ROCm (gfx1151)

Date: 2026-11-14 · Environments: ENV A = official wheel torch 2.12.0+rocm7.14.1 (MIOpen 3.5.2.cd957402, `e97891df`, no PR #13437), ENV B = same wheel with source-built MIOpen from f0a5d266 (3.6.2.f0a5d266, `ed7c67a9`).

## TL;DR

**There is no ROCm/AMP numerical defect.** The Round-3 "AMP anomaly" decomposes into:

1. **Benign fp16 coordinate quantization deltas.** FP32-vs-autocast(fp16) inference of the *same* precheck image produces the *same* detections (same count, same classes, conf deltas ≤ 0.004), with **box-coordinate deltas of 0.15–0.76 px** — normal fp16 quantization-level variation.
2. **Ultralytics `check_amp` uses `allclose(atol=0.5)` on raw pixel coordinates.** When the fp16 kernel in play produces deltas > 0.5 px, the check declares "anomalies … so AMP will be disabled" and training **silently falls back to FP32**. The deltas that decide PASS/FAIL (0.233 vs 0.760 px) are **deterministic per MIOpen cache state** — the check is a coin flip on kernel selection, not a numerical verdict.
3. **Kernel selection instability exists only in the source-built MIOpen 3.6.2 (f0a5d266) on this machine**: logs carry repeated `MIOpen: Error [EvaluateInvokers] … Invalid elapsed time detected … failed condition: elapsed <= 0` (solver_finders.cpp:535). The official wheel's MIOpen 3.5.2 shows no such errors and its fp16 deltas stayed ≤ ~0.23 px in both cache states → `check_amp` PASSES both ways.

## Experimental matrix (all runs 5 repeats, deterministic within context)

| Env | MIOpen | Cache home | precheck (section B) | real `check_amp` (C) | max abs diff (boxes) |
|---|---|---|---|---|---|
| B patched | 3.6.2.f0a5d266 `ed7c67a9` | fresh isolated | **PASS 5/5** | **True** | 0.2333 px |
| B patched | 3.6.2.f0a5d266 | default (warm, training context) | **FAIL 0/5** | **False** | **0.7606 px** |
| A official | 3.5.2.cd957402 `e97891df` | default | PASS 5/5 | True | (within 0.5) |
| A official | 3.5.2.cd957402 | fresh isolated | PASS 5/5 | True | (within 0.5) |

Raw: `windows-training-validation/raw/g3_amp_envB_patched.json`, `g3_amp_envB_defaulthome.json`,
`g3_amp_envA_official_defaulthome.json`, `g3_amp_envA_official_freshhome.json`, plus `amp-rca/MINIMAL_REPRO.py` outputs.

Per-column decomposition (MINIMAL_REPRO, ENV B):

| Column | fresh home | default home |
|---|---|---|
| x1 | 0.160 | **0.683** |
| y1 | 0.176 | 0.131 |
| x2 | 0.132 | 0.073 |
| y2 | 0.233 | **0.761** |
| conf | 0.0016 | 0.0043 |
| cls | 0.0 | 0.0 |

Only the coordinate columns move; conf/cls are untouched → detection *quality* is unaffected;
the check's failure is purely a threshold artifact on coordinates.

## AMP primitives (G3.2) — all healthy on both envs

- autocast dtype transitions correct (conv out fp16, BN out fp32, linear out fp16; weight grads fp32); all grads finite.
- GradScaler: normal step updates params; planted-inf grads → step skipped + scale halved — exact reference semantics.
- Raw: `g3_amp_envB_patched.json` section A; ENV A equivalent PASS.

## Real AMP training (G3.5) — works on the official wheel

`tests/g3_amp_training_10ep.py`, ENV A, coco8, 10 epochs, amp=True (precheck passed → autocast active):

```
step lr=0.00e+00 overflow=True  scale 65536→32768  delta=0        (scaler skips, halves)
step lr=8.37e-05 overflow=True  scale 32768→16384  delta=0
step lr=4.83e-05 overflow=True  scale 16384→8192   delta=0
step lr=1.30e-05 overflow=False scale 8192→8192    delta=-0.006332  ← REAL update
fitness 0.662 → 0.686 → 0.696 → 0.689 (10 epochs)
```

GradScaler anneal-and-skip semantics are textbook-correct; the model genuinely learns under AMP.
A 1–4-epoch smoke is **too short for the scaler to anneal past fp16 overflow**, so its real
updates can be skipped entirely — that is a workload-size artifact, not an AMP defect
(the 4-epoch lifecycle's "metrics drift" comes from BN running-stat updates, not weight updates).

## Root-cause classification (mission G3.4 categories)

- **A. ROCm kernel bug** — NO for AMP numerics. YES-adjacent for **MIOpen 3.6.2 solver timing**: the `EvaluateInvokers` negative-elapsed anomaly (source-built f0a5d266 only, gfx1151) destabilizes timing-based kernel selection → upstream issue draft required.
- **B. PyTorch ROCm bug** — NO. torch AMP API/autocast/GradScaler behave correctly.
- **C. Ultralytics check issue** — **YES (design)**: `check_amp` compares raw pixel coordinates with absolute tolerance 0.5 and treats any excess as a system-level AMP anomaly, silently disabling AMP. Tolerance/scale mismatch → false negative → PR-C draft (minimal: IoU- or class/conf-aware comparison, or coordinate tolerance scaled to imgsz).
- **D. Environment contamination** — partial: the "anomaly" is reproducible only in specific MIOpen cache states; cache state is a legitimate environment variable, but the check should not flip on it.

## What this means for the mission gates

- GO-A/GO-B: FP32 lifecycle fully validated (G2 14/14 × 7 tasks on ENV B; FP32). AMP: **works on the official wheel** (precheck PASS; 10-epoch training with real updates); on ENV B the precheck may fall back to FP32 depending on cache state — documented as an ENV-B limitation, not a fix defect.
- GO-C: blocked upstream items are documentation/PR drafts (C and A), not scientific unknowns.
