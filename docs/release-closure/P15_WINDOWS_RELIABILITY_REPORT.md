# P15.6 — Windows Training Reliability (2026-11-15, gfx1151, official released stack)

All legs are fresh-process executions on the official stack (torch 2.12.0+rocm7.14.1 + released ultralytics 8.4.182), evidence JSONs in `release-provenance/raw/p15_gfx1151/`. Settings were fixed by the frozen contract before execution; no passing-only settings were selected after observing failures.

## Reliability matrix

| # | Scenario | Result | Evidence |
|---|---|---|---|
| 1 | Fresh-process training (smoke COCO8 2 ep, workers=0) | **PASS** (23.4 s) | `p15_smoke_w0.json` |
| 2 | Repeated run after restart (fresh process each leg) | **PASS** ×4 legs | sequential JSONs |
| 3 | Fresh vs warm cache (w2 fresh 23.5 s / warm 23.1 s) | **PASS** — no cache pathology; timings recorded | `p15_smoke_w2*.json` |
| 4 | workers=0 | **PASS** | `p15_smoke_w0.json` |
| 5 | workers=2 and workers=4 | **PASS** ×2 | `p15_smoke_w2.json`, `p15_smoke_w4.json` |
| 6 | True AMP training | **PASS** (autocast engaged, 8/8 real updates; see `P15_AMP_NUMERICAL_ACCEPTANCE.md`) | `amp_probe.json` |
| 7 | Representative extended training (30 ep, COCO128, seed 0, workers 2) | **PASS** — full curve 0.4927→0.5980→0.5851 mAP50-95, no NaN/inf, no backend failure | `runs/p15/p15_30ep_w2/` + `orchestrate_train30.log` |
| 8 | Checkpoint save/reload | **PASS** — best.pt/last.pt written; SHA256 recorded (`best b606f877…`); `YOLO(best.pt)` reload → prediction | `p15_finalcheck_*.json` |
| 9 | Deliberate process interruption | **PASS** — hard `Stop-Process -Force` on PID 11452 after epoch ≥ 20 (21 rows on disk); `process_alive_after_kill: False`; `last.pt` intact | orchestrator log |
| 10 | Resume in a NEW process | **PASS** — "Resuming … from epoch 22 to 30"; args show restored state (`lr0=0.000119` scheduler position, optimizer state from last.pt); rows 22 → 31 (30 epochs complete) | `p15_resume_p15_30ep_w2.json` + resume console |
| 11 | Final validation and inference | **PASS** — best.pt val mAP50-95 0.5949 / mAP50 0.7823; reload + bus.jpg inference → 6 boxes | `p15_finalcheck_*.json` |
| 12 | GPU OOM behavior | carried evidence (P13/P14 error-UX legs); no new OOM leg this session | `P14_GOLDEN_PATH_EXECUTION_REPORT.md` |
| 13 | Missing model/dataset behavior | **PASS (carried)** — actionable message, no silent fallback | P14 error-UX evidence |
| 14 | Wrong/unsupported runtime package reporting | carried (P14 CPU-only refusal exit 2) | `P14_GOLDEN_PATH_EXECUTION_REPORT.md` |
| 15 | Unsupported-device reporting | carried | P13/P14 |

## Windows-specific observations (P15 session)

- **DataLoader multiprocessing**: workers 0/2/4 all clean under Windows spawn (`multiprocessing.freeze_support()` in the driver, mirroring golden-path conventions); no worker crash, no handle leak symptoms.
- **Process teardown**: hard kill left no live training process (verified `process_alive_after_kill: False`); P13-era ghost processes remain a separate carried issue (E5, owner: machine restart) — they did not affect any P15 leg (all ran on ENV A official wheel; MIOpen.dll lock only affects ENV B source-built setups).
- **Checkpoint atomicity**: interruption at epoch 21 left `last.pt` loadable and resume continued cleanly to completion — no corrupted checkpoint observed.
- **MIOpen cache**: warm-cache leg showed no failure and comparable time (23.1 s vs 23.5 s fresh) — no fresh-cache-only regression.
- **Security software**: no Smart App Control / Defender interference encountered on any official-channel artifact this session.

## Failure ledger

No new P15 failure occurred in any required leg. Historic carried issues (unchanged owners): ENV B DLL lock (machine restart), FDB root cause UNRESOLVED (P13 archive), official-wheel no-STL blocker (AMD release chain).

## Verdict

**PASS for gfx1151** on all runnable required scenarios (fresh/restart/cache/workers/AMP/extended/checkpoint/interrupt/resume/final), with carried evidence for error-UX legs and BLOCKED_HARDWARE for the second class.
