# CHECKPOINT AUDIT — G4.3 checkpoint & recovery integrity

Basis: G2 lifecycle t09/t10/t11/t12 records (7 tasks) + G4 long-run final checkpoint.

## Findings

1. **Checkpoint semantics (ultralytics 8.4.182, verified)**:
   - During training, `last.pt` is written at every epoch end WITH optimizer state (resumable) — verified: interrupt-time checkpoint had `epoch=1, optimizer≠None`.
   - On training completion, `last.pt` is **final-stripped** (`epoch=-1`, optimizer removed, resume rejected by design); `best.pt` retains full model+train_args — verified by t12 resume working from the interrupt-time last.pt and t09's post-completion state.
2. **Resume correctness (T12, all 7 tasks)**: separate-process resume from the interrupted last.pt completed the planned 4 epochs with results.csv continuity (rows appended, no duplication).
3. **Reload equality (T15, all 7 tasks)**: two independent YOLO(best.pt) instances produce **bit-identical val metrics** (max diff ≤ 1e-12) — deterministic eval, valid checkpoint serialization.
4. **Cold start / warm start**: covered by G1's isolated-cache-home legs (cold) and the G2/G4 warm runs; model download/cache reuse exercised by the 6 asset downloads + dataset auto-download (coco128/dota8/cityscapes8/depth8/coco8-seg/coco8-pose).
5. **Non-divisible last batch / batch sizes**: coco8 (8 imgs, batch 16 → single partial batch) exercised every G2 run; dota8 (8 imgs) and imagenette (9469) cover both extremes.
6. **Unexpected process termination**: verified *accidentally-and-honestly* — the force-killed G3 probe left an unkillable zombie holding MIOpen.dll (INCIDENT file); new GPU processes unaffected. Graceful process-exit hang observed once in ~20 GPU processes (exit-time HIP cleanup), recorded as a stability observation with zero data loss (results already flushed).
7. **OOM handling**: not exercised (no OOM encountered on 78 GB unified memory with these workloads) — **NOT_RUN**, noted as limitation.

## Remaining gaps (honest)

- GPU OOM recovery path: NOT_RUN (workloads too small to trigger).
- Multi-GPU DDP Windows: NOT_RUN (single iGPU; explicitly out of scope per mission §9).
- Checkpoint portability across machines (Linux↔Windows): NOT_RUN (single machine).
