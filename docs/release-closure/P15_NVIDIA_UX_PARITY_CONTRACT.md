# P15.5 — NVIDIA UX Parity Contract (PRE-REGISTERED, FROZEN 2026-11-15)

This contract is written and frozen **before** any NVIDIA measurement exists. No criterion may be
reinterpreted or relaxed after results are seen. The executable reference implementation is
`scripts/p15/nvidia_reference.py` (runs the identical legs on an NVIDIA Windows host and emits the
same evidence schema as the Radeon driver `scripts/p15/p15_run.py`).

## 0. Scope and honesty rules

- PASS/FAIL is functional UX parity, **not** GPU throughput. Hardware speed differences alone are not FAIL.
- The NVIDIA side must be measured on real hardware with officially supported NVIDIA software
  (CUDA wheel from pytorch.org). A missing comparator is **NVIDIA_COMPARISON_BLOCKED_HARDWARE** —
  never fabricated.
- Backend package versions (CUDA vs ROCm wheels) necessarily differ; they are recorded, not compared.
- If batch sizes differ due to hardware memory, the difference is reported; no performance conclusion is drawn.

## 1. Kept constant (both sides)

| Factor | Value |
|---|---|
| Windows | Windows 11 (26200-class build recorded per host) |
| Python | 3.13 (same minor version on both) |
| Ultralytics | **same released PyPI version on both sides** (8.4.182 for the Radeon P15 run; NVIDIA side must use the identical version unless unsupported, which is itself a parity finding) |
| Model / checkpoint | `yolo26n.pt` (same file, SHA256 recorded) |
| Dataset / split | COCO128 train + COCO128 val (same bundled split) |
| Image size | 640 |
| Epochs | 30 (representative), 2 (smoke) |
| Seed | 0 |
| Hyperparameters | defaults only; `device=0` explicit; `workers` recorded (2 for representative) |
| Validation protocol | `model.val(data="coco128.yaml", imgsz=640)` on `best.pt` |
| Recovery procedure | `Stop-Process`-class hard kill after epoch ≥ 20, then new-process `YOLO(last.pt).train(resume=True)` |

## 2. Required dimensions and pre-registered pass criteria

| # | Dimension | Measurement | PASS criterion |
|---|---|---|---|
| A | INSTALL | Follow public official docs only (NVIDIA: pytorch.org CUDA wheel + `pip install ultralytics`; Radeon: AMD ROCm wheel index + `pip install ultralytics`) | No undocumented patches, no manual DLL swaps, no private wheel URLs |
| B | TRAIN COMMAND | `yolo` CLI / `YOLO("yolo26n.pt").train(device=0)` from docs | Same standard command works; no AMD-only model-code changes |
| C | VALIDATE / PREDICT | `model.val(...)`, `model.predict(...)` | Same API/CLI semantics; valid metrics / detections |
| D | AMP | amp-probe leg (autocast dtype engagement + GradScaler skip/update semantics + check_amp verdict) | Genuine AMP (autocast engaged, ≥1 real optimizer update); no FP32-passed-as-AMP |
| E | CHECKPOINTS | best.pt/last.pt existence, SHA256, reload via `YOLO(best.pt)` | Save/reload correct on both sides |
| F | RESUME | hard kill after epoch ≥ 20 → new-process resume | Training state restored: row count continues (≥21 rows), no duplicated epochs, final val runs |
| G | ERROR MESSAGES | (1) `device=cpu` forced on GPU-only golden path → clear refusal; (2) missing/typo dataset → actionable message; (3) corrupt checkpoint → precise exception | First-time developer can identify & fix each, per leg's console text |
| H | USER INTERVENTION | count of undocumented manual operations during A–G | **0** |
| I | REPRODUCIBILITY | rerun of the documented procedure by the same steps | All artifacts + commands retained; second fresh-process smoke succeeds |
| J | RELIABILITY | representative 30-epoch run completes; smoke legs w0/w2/w4; warm cache | No unexplained critical backend failure in any required leg |

## 3. Secondary measurements (reported, never pass/fail)

Install duration, time-to-first-GPU-train-step, per-epoch duration, peak GPU memory, recovery time.

## 4. Execution status

| Side | Status |
|---|---|
| Radeon (gfx1151, official released stack: torch 2.12.0+rocm7.14.1 + ultralytics 8.4.182) | executed in P15 (see `P15_NVIDIA_VS_RADEON_RESULTS.json`, legs filled from `release-provenance/raw/p15_gfx1151/`) |
| NVIDIA Windows | **NVIDIA_COMPARISON_BLOCKED_HARDWARE** — no physical NVIDIA Windows machine available to this project. `scripts/p15/nvidia_reference.py` is ready; GATE 5 remains unexecuted until someone runs it on real hardware and submits the JSON. |

## 5. Anti-fabrication clause

No NVIDIA baseline value may be invented, extrapolated from Linux runs, or taken from published
benchmarks. `P15_NVIDIA_VS_RADEON_RESULTS.json` carries `"null"` + `"NOT_RUN"` for every NVIDIA leg
until real hardware evidence exists. UX parity is **not claimed** in any P15 document.
