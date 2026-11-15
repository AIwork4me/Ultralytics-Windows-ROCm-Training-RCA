# P15.3 — True AMP and Numerical Acceptance (2026-11-15, gfx1151)

Hardware class: **AMD Radeon 8060S / gfx1151** (the only physically available class; Class B = BLOCKED_HARDWARE).
Stack: official released channels only — `torch 2.12.0+rocm7.14.1` (AMD official wheel) + **released ultralytics 8.4.182 (PyPI)** + driver 32.0.22032.6002 + Windows 26200. Raw evidence: `release-provenance/raw/p15_gfx1151/`.

## Pre-registration (frozen before the run)

The kept-constant matrix was frozen in `P15_NVIDIA_UX_PARITY_CONTRACT.md` §1 **before** any P15 GPU leg executed: yolo26n + COCO128 + 640 imgsz + 30 epochs + seed 0 + default hyperparameters + `device=0` + workers 2. No threshold was chosen after seeing results; quality is reported as a measured learning curve (no benchmark claim — no Linux/NVIDIA reference machine exists, carried INCONCLUSIVE scope from P13).

## 1. AMP precheck

`check_amp` (upstream per-layer relative-norm probe, post-#26967 design) on the real device: **PASS → True** (`amp_probe.json.check_amp_verdict`); the 30-epoch trainer's own precheck also ran with `amp=True`.

## 2. Genuine autocast execution (not just a passing check)

Same Conv2d input on HIP device:

| Path | Output dtype |
|---|---|
| FP32 | `torch.float32` |
| under `torch.autocast("cuda")` | **`torch.float16`** |

⇒ autocast genuinely engages on the ROCm/HIP backend (`amp_probe.json.autocast_engaged = true`). FP32 execution is not being reported as AMP.

## 3. GradScaler behavior and real optimizer updates

8 training steps on a trainable head, per-step parameter L2 checksums:

| Metric | Result |
|---|---|
| Real optimizer updates | **8/8 steps** (`params_changed: true` each step, checksums strictly change) |
| Scale trajectory | 65536 → 65536 (no overflow on this synthetic probe — honest note: overflow *skip* semantics were demonstrated with the anneal 65536→2048 in P9's per-step tracker `g2_detect_amptrack_*` on this same stack; this P15 probe's stable loss simply triggered no overflow) |
| YOLO param tensors | 366 (2,408,932-parameter yolo26n) — count recorded; per-parameter delta tracking carried from P9 evidence (all tensors changed per step) |

`AMP_PASS` — with the explicit scope note: precheck True + autocast engaged + real measured parameter updates; overflow-skip semantics carried from P9 evidence rather than re-demonstrated in the P15 probe.

## 4. Representative training, learning, and validation (fresh P15 run)

30-epoch COCO128 run (seed 0, workers 2, AMP enabled) — results.csv SHA256 recorded in the run summary:

- Learning curve (per-epoch mAP50-95): **0.4927 (ep1) → 0.5980 (ep22 peak) → 0.5851 (ep30)** — unambiguous model learning (+0.092 absolute from epoch 1), consistent with P14's independent 20-epoch run on the same stack (0.4919 → 0.5603): both runs start ≈0.49 and climb substantially; no unexplained numerical degradation, no NaN/inf.
- Validation of `best.pt` on COCO128 val: **mAP50-95 0.5949, mAP50 0.7823**.
- Cross-run variability context: P14 20-epoch (same seed/data) ended 0.5603 vs P15 30-epoch 0.5851-0.5980 — different lengths/dates, both healthy curves; fine-grained threshold claims remain out of scope by pre-registration (no reference machine).

## 5. States (per mission vocabulary)

- gfx1151: **AMP_PASS**
- Class B (gfx1100/RDNA3): **NOT_RUN** (BLOCKED_HARDWARE — no inference of Class A → B permitted)

## 6. Verdict

True AMP training on gfx1151 with the official released stack: **PASS** for the available class. GATE-quality AMP evidence for a second architecture class remains blocked on hardware, not software.
