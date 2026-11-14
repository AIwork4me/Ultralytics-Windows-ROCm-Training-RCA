# G2 VERDICT — Complete Ultralytics Training Lifecycle

Date: 2026-11-14 · Env B (source-built patched MIOpen `ed7c67a9`, torch 2.12.0+rocm7.14.1, ultralytics 8.4.182) · GPU provenance: per-task in-process loaded-DLL probe (all `ed7c67a9…`) · **Verdict: PASS (FP32 track, 7/7 tasks)** · AMP track: runs PASS; AMP effectiveness differs by environment (see G3)

## Task matrix verified against installed source (G2.1 — no guessing)

`ultralytics 8.4.182` supports seven YOLO26 training tasks — verified via `guess_model_task()` against the installed package and the per-task model yamls in `cfg/models/26/`:
**detect / segment / classify / pose / obb / semantic / depth** (task names `semantic` and `depth` for the two new heads). No `NOT_SUPPORTED_BY_VERSION` entries.

Official smoke datasets (auto-downloaded, checksums by ultralytics): `coco8`, `coco8-seg`, `coco8-pose`, `dota8`, `cityscapes8`, `depth8`; classify uses public **imagenette2-160** (sha256 `64d0c4859f35a461889e0147755a999a48b49bf38a7e0f9bd27003f10db02fe5`, 9469 train / 3925 val — documented classify example dataset; no smaller official one ships).

## Lifecycle T01–T15 per task (FP32, workers=0)

Harness: `tests/g2_lifecycle.py` + `scripts/g2_runner.py`. T12 = interrupt after epoch 1 of 4 via callback-raised exception (ultralytics saves the resumable last.pt *before* `on_fit_epoch_end`, so this aborts without the final-checkpoint strip — verified `epoch=1 + optimizer present`), then a **separate process** resumes and must complete 4 epochs.

| Task | Weights | Result | Evidence |
|---|---|---|---|
| detect | yolo26n.pt | **14/14 PASS** | `raw/g2_detect_fp32.json` (moved: workers2/4 copies share record) — canonical record re-created in extras chain |
| segment | yolo26n-seg.pt | **14/14 PASS** | `raw/g2_segment_fp32.json` |
| classify | yolo26n-cls.pt | **14/14 PASS** | `raw/g2_classify_fp32.json` |
| pose | yolo26n-pose.pt | **14/14 PASS** | `raw/g2_pose_fp32.json` |
| obb | yolo26n-obb.pt | **14/14 PASS** | `raw/g2_obb_fp32.json` |
| semantic | yolo26n-sem.pt | **14/14 PASS** | `raw/g2_semantic_fp32.json` |
| depth | yolo26n-depth.pt | **14/14 PASS** | `raw/g2_depth_fp32.json` |

Per task: T01 pretrained GPU inference · T03 init · T04 1-epoch smoke · T05 4-epoch interrupted · T06 loss finite every epoch · T07 backward gradients finite (post-warmup steps) · T08 optimizer really updates params (ΔΣ|θ|>0 at lr>0) · T09/T10 checkpoints (integrity incl. final-strip semantics) · T11 reload · T12 resume completes 4 epochs · T13 val of saved model · T14 predict of saved model · T15 metrics identical across reload.

Example final metrics (detect, 4 epochs, mAP50 = 0.9418 / mAP50-95 = 0.6704): `raw/g2_detect_envA_amptrack.json` t13.

## Windows DataLoader (G2.3)

- detect lifecycle × **workers=2** → 14/14 PASS (`raw/g2_detect_workers2.json`)
- detect lifecycle × **workers=4** → 14/14 PASS (`raw/g2_detect_workers4.json`)
- No spawn deadlocks; runs complete; no `__main__` guard issues (scripts run as files).
- Limitation: workers=0 default covers the canonical record; 2/4 verified on detect only (representative spawn path — same loader classes across tasks).

## AMP track (G2.4) — separate runs, separate records

- ENV B amp=True lifecycle: 14/14 PASS, but `trainer_amp_effective=False` — **check_amp fell back to FP32** (see G3: cache-state-dependent precheck). Runs complete, losses finite; NOT an AMP PASS.
- ENV A amp=True lifecycle: 14/14 PASS with **AMP effective** (official wheel precheck passes). 10-epoch probe proves real weight updates under AMP (`raw/g3_amp10_envA.json`). FP32 PASS never claimed as AMP PASS anywhere.

## Honest changelog (defects found in the harness, all root-caused before rerun)

1. `-I` isolation broke PyYAML import (user-site dependency) → G2 runs without `-I`.
2. 8.4.182 removed the `on_before_zero_grad` callback invocation → step-wrapper hook on `trainer.optimizer_step` (read-only).
3. Warmup starts at lr=0: the first optimizer step legitimately changes nothing → t08 any-step-changed semantics with SKIP status for warmup-only phases; authoritative record from the resume stage (lr>0 step, ΔΣ|θ|=0.012).
4. Graceful `trainer.stop=True` **finalizes** the checkpoint (epoch=-1, optimizer stripped, non-resumable) — replaced with callback-exception interruption; resumability asserted at interrupt time.
5. OBB/semantic/depth results carry `.obb`/`.masks`, not `.boxes` — task-agnostic detection counting.
6. Ultralytics 8.4.182 inserts the task subdir when `project=` is passed explicitly (`runs/detect/runs/multi`) — default project used instead.

## G2 PASS condition — met (FP32 track)

All seven currently-supported tasks complete the full T01–T15 lifecycle on the real Windows ROCm GPU with parameter updates, checkpoint integrity, resume, and metric persistence. AMP is validated separately in G3 (works on official wheel; cache-state-dependent fallback on ENV B documented).
