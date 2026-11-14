# PERFORMANCE REPORT — G4.4 matched A/B + honest scope

## Matched A/B — FP32 vs AMP (official wheel ENV A, identical seed/data/epochs)

`windows-training-validation/tests/g4_perf_ab.py` · coco8 detect 10 epochs · batch 16 · workers 2 · 2026-11-14

| Mode | Mean epoch | Train imgs/s | Peak VRAM | Final fitness |
|---|---|---|---|---|
| FP32 | 1.69 s | 4.7 | 1.28 GB | 0.6725 |
| AMP (effective) | 2.71 s | 3.0 | **0.86 GB** | 0.6889 |

| Ratio | Value |
|---|---|
| AMP vs FP32 epoch time | **1.60× (AMP slower on this workload)** |
| AMP VRAM saving | **−33%** |

### Interpretation constraints (binding)

- **Workload size invalidates throughput conclusions**: coco8 = 8 images; per-epoch time is dominated by dataloader/setup overheads and (for AMP) GradScaler overflow-skips at initial scale — this A/B measures *relative behavior on identical small work*, NOT throughput rankings. G3's 10-epoch probe showed the AMP scaler skipped 3 of 4 real-step opportunities in the first epochs.
- **Fitness 0.6725 vs 0.6889 is trajectory nondeterminism across precision paths** (different fp16 rounding → different update sequence), not a quality claim in either direction.
- **The VRAM reduction (−33%) is the robust, expected AMP effect.**
- No old-MIOpen baseline exists for training workloads (pre-fix DLL cannot run BN training) → **no "fix vs no-fix" performance claim is possible** (mission rule honored: no fabricated baseline).
- The ISA-equality evidence from phase5_8 remains exactly what it was: machine-code equality of retained kernels, **not** an end-to-end performance statement.

## Raw samples

`raw/g4_perf_ab_envA.json` (per-run records) + per-epoch CSVs retained in `g2_work/runs/detect/perfab_{fp32,amp}/results.csv` (regenerable run dirs; JSON carries the authoritative numbers).

## Cross-check note (epoch-time source)

G4.1 long run (ENV B): epoch 0 = 122.8 s (cold HIPRTC compile) vs steady state 6.8 s — cold-compile latency is a one-time cost per cache home; warm steady-state is the comparable figure.
