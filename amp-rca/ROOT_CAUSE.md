# ROOT CAUSE — Ultralytics AMP anomaly on Windows ROCm (gfx1151)

Date: 2026-11-14 · Environments: ENV A = official wheel torch 2.12.0+rocm7.14.1 (MIOpen 3.5.2.cd957402, `e97891df`, no PR #13437), ENV B = same wheel with source-built MIOpen from f0a5d266 (3.6.2.f0a5d266, `ed7c67a9`).

## TL;DR

**There is no ROCm/AMP numerical defect.** The Round-3 "AMP anomaly" decomposes into:

1. **Benign fp16 coordinate quantization deltas.** FP32-vs-autocast(fp16) inference of the *same* precheck image produces the *same* detections (same count, same classes, conf deltas ≤ 0.0043), with **box-coordinate deltas of 0.07–0.76 px** (archived per-column range 0.0730–0.7606; run-level maxima 0.233/0.761) — normal fp16 quantization-level variation.
2. **Ultralytics `check_amp` uses `allclose(atol=0.5)` on raw pixel coordinates.** When the fp16 kernel in play produces deltas > 0.5 px, the check declares "anomalies … so AMP will be disabled" and training **silently falls back to FP32**. The deltas that decide PASS/FAIL (0.233 vs 0.760 px) are **deterministic per MIOpen cache state** — the check is a coin flip on kernel selection, not a numerical verdict.
3. **The `EvaluateInvokers` negative-timing anomaly is repeated on the source-built MIOpen 3.6.2 (f0a5d266) and rare-but-present on the official 3.5.2** (audit re-scope M2): logs carry repeated `MIOpen: Error [EvaluateInvokers] … Invalid elapsed time detected … failed condition: elapsed <= 0` (solver_finders.cpp:535; 4× in `raw/g2_pose_main.log`), and one identical error was observed in an aborted official-wheel amptrack attempt (`raw/scrambled_logs_20261114/g2_detect_envA_amptrack_main.log:150`; 0 occurrences in the clean official re-run). The official wheel's fp16 deltas also vary with cache state — 0.264 px (fresh) vs 0.423 px (default) — but **stay below the 0.5 px threshold in both states** → `check_amp` PASSES both ways. What is ENV-B-specific is the delta magnitude *crossing* the threshold in the default-cache state.

## Experimental matrix (all runs 5 repeats, deterministic within context)

| Env | MIOpen | Cache home | precheck (section B) | real `check_amp` (C) | max abs diff (boxes) |
|---|---|---|---|---|---|
| B patched | 3.6.2.f0a5d266 `ed7c67a9` | fresh isolated | **PASS 5/5** | **True** | 0.2333 px |
| B patched | 3.6.2.f0a5d266 | default (warm, training context) | **FAIL 0/5** | **False** | **0.7606 px** |
| A official | 3.5.2.cd957402 `e97891df` | default | PASS 5/5 | True | 0.4234 px (below 0.5) |
| A official | 3.5.2.cd957402 | fresh isolated | PASS 5/5 | True | 0.2642 px (below 0.5) |

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

GradScaler anneal-and-skip semantics are textbook-correct. **Interpretation note (audit M5, corrected)**: in this 10-epoch probe 3 of 4 step opportunities were overflow-skipped and the single real weight update landed at the final epoch, after which fitness *decreased* (0.696→0.689); all fitness gains occurred at *skipped-step* epochs — attributable to BN running-stat updates, the same mechanism as the 4-epoch drift below. What this probe therefore establishes is **correct scaler anneal semantics + anomaly-free AMP training completion + ≥1 real update**, not demonstrated weight-learning.
A 1–4-epoch smoke is **too short for the scaler to anneal past fp16 overflow**, so its real
updates can be skipped entirely — that is a workload-size artifact, not an AMP defect
(the 4-epoch lifecycle's "metrics drift" comes from BN running-stat updates, not weight updates).

## Root-cause classification (mission G3.4 categories)

- **A. ROCm kernel bug** — NO for AMP numerics. YES-adjacent for **MIOpen solver timing**: the `EvaluateInvokers` negative-elapsed anomaly is repeated on source-built 3.6.2 f0a5d266 and rare-but-present on official 3.5.2 (gfx1151; one occurrence in an aborted official-wheel attempt, none in clean runs) — it destabilizes timing-based kernel selection → upstream issue draft required.
- **B. PyTorch ROCm bug** — NO. torch AMP API/autocast/GradScaler behave correctly.
- **C. Ultralytics check issue** — **YES (design)**: `check_amp` compares raw pixel coordinates with absolute tolerance 0.5 and treats any excess as a system-level AMP anomaly, silently disabling AMP. Tolerance/scale mismatch → false negative → PR-C draft (minimal: IoU- or class/conf-aware comparison, or coordinate tolerance scaled to imgsz).
- **D. Environment contamination** — partial: the "anomaly" is reproducible only in specific MIOpen cache states; cache state is a legitimate environment variable, but the check should not flip on it.

## What this means for the mission gates

- GO-A/GO-B: FP32 lifecycle fully validated (G2 14/14 × 7 tasks on ENV B; FP32). AMP: **works on the official wheel** (precheck PASS; 10-epoch training with real updates); on ENV B the precheck may fall back to FP32 depending on cache state — documented as an ENV-B limitation, not a fix defect.
- GO-C: blocked upstream items are documentation/PR drafts (C and A), not scientific unknowns.
