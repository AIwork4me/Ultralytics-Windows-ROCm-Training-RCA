# P15.6b — Two Windows Radeon Architecture Classes (2026-11-15)

Status: **Class A (gfx1151) executed in P15 · Class B (gfx1100/RDNA3 discrete) BLOCKED_HARDWARE** ⇒ the two-class gate is NOT met.

## 1. Class A — AMD Radeon 8060S / gfx1151 (Ryzen AI MAX+ iGPU)

Officially supported for the tested stack (verified per P14 wheel audit + today's re-confirmation): Windows 11 26200, official AMD wheel `torch 2.12.0+rocm7.14.1` (whl-multi-arch channel), released ultralytics 8.4.182, driver 32.0.22032.6002.

P15 execution (official released stack, fresh processes, evidence in `release-provenance/raw/p15_gfx1151/`):

| Leg | Result |
|---|---|
| amp-probe (autocast engagement, GradScaler skip/update semantics, check_amp) | **PASS** (autocast fp16 engaged; ≥1 real optimizer update) |
| smoke workers=0 / 2 / 4 / warm (COCO8, 2 ep) | **PASS ×4** (fresh-process runs completed) |
| representative 30-epoch COCO128 seed=0 workers=2 | see `P15_AMP_NUMERICAL_ACCEPTANCE.md` / `P15_WINDOWS_RELIABILITY_REPORT.md` (P15 run) |
| interrupt ≥ epoch 20 → new-process resume | see P15_WINDOWS_RELIABILITY_REPORT.md |
| finalcheck (val + best.pt reload + inference) | see P15_WINDOWS_RELIABILITY_REPORT.md |

Historical depth (preserved, not rewritten): P9/P13/P14 FP32 + AMP + resume evidence on the same class.

## 2. Class B — gfx1100 (Radeon RX 7900 XTX) / RDNA3 discrete

- **No physical hardware available** to this project: **BLOCKED_HARDWARE**.
- Support caveat carried from P14: the official AMD Windows support matrix for the tested wheel versions must be checked per-release before any claim; a class that is not officially supported by the exact Windows+driver+wheel combination **cannot count** toward the gate.
- A Linux W7900 or any same-architecture substitute does NOT satisfy this gate; an alternative genuinely distinct class (e.g., RDNA4) would qualify only with real Windows hardware evidence.

## 3. Gate consequence

GATE 1 remains satisfied **for one class only**. The mission's ultimate success criterion (two distinct officially supported Windows Radeon architecture classes independently completing the full workflow) is **NOT_MET** on hardware availability, independent of software state.

## 4. What unblocks

Physical access to a second, officially supported Windows Radeon architecture class (gfx1100/RDNA3 or RDNA4), then run the identical leg sequence (same driver contract as §1) and record evidence under `release-provenance/raw/p15_<class>/`.
