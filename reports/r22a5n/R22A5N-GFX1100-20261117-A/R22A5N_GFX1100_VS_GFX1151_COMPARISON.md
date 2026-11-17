# R22A5N_GFX1100_VS_GFX1151_COMPARISON.md

Cross-architecture comparison for mission R22A.5N (Official Nightly physical
prequalification). Purpose: confirm **functional portability of the MIOpen
PR #13437 fix** across RDNA3 dGPU (gfx1100) and Strix Halo APU (gfx1151) on
the SAME audited official nightly bytes. It is explicitly NOT a compute
benchmark and NOT a claim that either architecture must reproduce the
other's numerical trajectory.

Reference gfx1151 evidence: `reports/r22a5n1/R22A5N1-GFX1151-20261117-B/`
(hardened R22A.5N.1 pack; engine `r22a5n1-acceptance-v2`).
gfx1100 evidence: `reports/r22a5n/R22A5N-GFX1100-20261117-A/`
(mission-profile engine `r22a5n1100-acceptance-v1`, hardened G5/G7).

## Binary identity (shared, byte-verified independently on both hosts)

| Artifact | Value | gfx1151 | gfx1100 |
|---|---|---|---|
| SDK Libraries wheel | `rocm_sdk_libraries-10.3.0a20261116-py3-none-win_amd64.whl` | sha `b11baad9…599f0` verified | sha `b11baad9…599f0` re-verified from this host's own download |
| Embedded MIOpen.dll | build `3.6.3.25f28906` | sha `f9312c3e…0cb6` verified | sha `f9312c3e…0cb6` re-verified (child-process load, G0/G1/G2/G3 receipts) |
| Fix ancestry f0a5d266→25f28906 | behind_by=0, ahead_by=1074 | live compare API | live compare API (re-run 2026-11-17) |
| GPU-specific device wheels | gfx1151 set | gfx1100 set (never shared — profile rule §5.4) | |

## Gate matrix

| Gate | gfx1151 (R22A.5N.1-B) | gfx1100 (this mission) |
|---|---|---|
| PKG package set | PASS (cp313) | PASS (cp312, 46-wheel lock, installed-vs-lock diff empty, pip check clean) |
| LK lock binding | PASS | PASS (both training receipts re-bound to committed lock bytes) |
| G0 runtime identity | PASS | PASS (child DLL `f9312c3e…`, RX 7900 XTX/gfx1100) |
| G1 no-STL candidate | PASS (1 cold trial) | PASS (**2 independent cold trials**, distinct PIDs 5424/11924 + distinct cold scratch homes) |
| G1 pre-fix control | OFFICIAL_PRE_FIX_EXPECTED_FAIL | OFFICIAL_PRE_FIX_EXPECTED_FAIL (`type_traits` ×2 in raw log; at-failure child DLL `e97891df…` marker=0 — byte-identical pre-fix control DLL as gfx1151's, per the official 7.14.1 wheel) |
| G2 core GPU ops | PASS | PASS (9/9 incl. FP16 GEMM + torchvision GPU NMS; no CPU fallback) |
| G3 YOLO training | PASS | PASS (YOLO26n, COCO128, 3 ep, imgsz 256, batch 8, workers 0, optimizer auto→AdamW fused) |
| G4 AMP | PASS | PASS (autocast float16 observed; 96 low-precision stem-conv samples) |
| G5 checkpoint resume | PASS — verdict `FULL_TRAINING_STATE_RESTORE_PASS` under pre-hardening semantics | PASS — verdict `RESUME_PASS_CORE_STATE_VERIFIED` under hardened fail-closed semantics (see below) |
| G7 workers=8 | PASS (16 spawn children) | PASS (16 simultaneous spawn_main children recomputed from raw 400-char census snapshots; orphan recomputed CLEAN) |
| Overall | `R22A5N1_GFX1151_NIGHTLY_EVIDENCE_AUDITED_PASS` | `R22A5N_GFX1100_NIGHTLY_EVIDENCE_AUDITED_PASS` |

## Training-behavior observations (NOT acceptance targets)

| Observation | gfx1151 | gfx1100 |
|---|---|---|
| AMP workers=0 steps (attempt/effective/inf-skip) | 11 / 7 / 4 | 11 / 7 / 4 |
| GradScaler backoffs | 4 | 4 |
| workers=8 steps (attempt/effective/inf-skip) | 11 / 7 / 4 | 11 / 6 / 5 |
| mAP50 per epoch (workers=0 run) | 0.48349 / 0.47785 / 0.47359 / 0.48451 | 0.48331 / 0.47806 / 0.47440 / 0.48426 |
| AMP training wall time | 32.6 s | 101.2 s |

Both runs converge to mAP50 ≈ 0.48 with near-identical epoch trajectories
(same data, seed and config) — close but **not identical**, as expected for
different silicon + Python ABI; no trajectory was forced to match. The
matching 11/7/4 workers=0 GradScaler shape on both architectures is an
observation, not a gate: the acceptance engines hardcode no counts and
recompute everything from per-step events.

## Honest semantic deltas found by THIS mission

1. **G5 verdict semantics hardened.** The R22A.5N.1 engine (PR #22 HEAD
   `568981d`) classifies `FULL_TRAINING_STATE_RESTORE_PASS` even when the
   checkpoint's scheduler state is `NOT_SERIALIZED_BY_UPSTREAM` — gfx1151's
   hardened-pack G5 carries that FULL verdict. Mission §1.2 for gfx1100
   requires fail-closed closure: the r22a5n1100 engine can only claim FULL
   when the scheduler state is ACTUALLY serialized AND restored, and
   independently re-observed on gfx1100 that 8.4.214 serializes
   optimizer/epoch/best_fitness/train_args/EMA/GradScaler but NOT the LR
   scheduler. gfx1100 therefore reports
   `RESUME_PASS_CORE_STATE_VERIFIED` with the limitation disclosed. The
   gfx1151 historical evidence is untouched; its FULL claim should be
   re-read under this stricter semantics during owner review.
2. **G1 now requires two independent cold candidate trials** (mission §7
   for gfx1100): both PASS with distinct process and cold-cache identities.
3. **G7 census evidence depth.** gfx1100's first workers=8 attempt exposed
   that 160-char census cmdlines truncate the real trainer's script name on
   redirector-venv topologies (this host's venv python trampolines to the
   uv base interpreter); the hardened raw-snapshot recompute correctly
   refused the gate. Capture widened to 400 chars; attempt 2 verified
   (16/16 spawn_main, single snapshot). Attempt 1 preserved and disclosed
   (`08_workers_reliability/attempt1_*` + incident note).

## Verdict

Both architectures PASS all gates on the SAME audited official 2026-11-16
nightly bytes, each on its own physical host, each independently audited:

`NIGHTLY_DUAL_ARCH_FUNCTIONAL_EVIDENCE_COMPLETE` — functional portability of
the PR #13437 fix across gfx1151 and gfx1100 is supported by dual-arch
physical evidence, pending owner review of both packs.

This is NOT `OFFICIAL_STABLE_PASS` and certifies nothing about the Stable
channel (still pre-fix at 10.1.0) or clean-Windows installability (G9).
