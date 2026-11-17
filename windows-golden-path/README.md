# Windows Golden Path Harness (R21)

**Status (2026-11-15): HARNESS VALIDATED on physical gfx1100 (RX 7900 XTX).
Golden Path itself remains BLOCKED_RELEASE — see verdicts below.**

Single entry point:

```powershell
.\run-golden-path.ps1 -Mode Preflight            # default; baseline only
.\run-golden-path.ps1 -Mode EngineeringReference # full R21 pipeline (isolated venv)
.\run-golden-path.ps1 -Mode OfficialCandidate -LockJson <resolved_wheel_lock.json>
.\run-golden-path.ps1 -Mode OfficialStable    -LockJson <resolved_wheel_lock.json>
.\run-golden-path.ps1 -Mode PrepareRelease       # channel scan, no GPU
```

No mode installs packages or starts GPU work by surprise; every mode prints
its runtime classification first. See [docs/architecture.md](docs/architecture.md).

## What this harness proved on 2026-11-15 (gfx1100 physical runs)

| Phase | Gate | Result |
|---|---|---|
| R21-A | provenance | fail-closed → ENGINEERING_REFERENCE (shim detected; official pre-fix DLL `e97891df…`, build `cd957402`, marker 0) |
| R21-A2 | torch/torchvision GPU | **PASS 9/9** (incl. nms via device wheel) |
| R21-D1 | no-STL, no shim | **OFFICIAL_PRE_FIX_EXPECTED_FAIL** — exact #3956 signature, cold cache, gfx1100 |
| R21-D2 | no-STL, shim | **ENGINEERING_REFERENCE_PASS** (same wheel bytes, only the disclosed shim differs) |
| R21-E1 | exact CLI `yolo train … device=-1` | **PASS** exit 0, GPU, AMP passed, ckpts hashed, ultralytics 8.4.214 |
| R21-E2 | optimizer audit | **PASS** (steps, named_parameters delta, per-step scaler history) |
| R21-E3 | interrupt→resume→reload | see evidence/r21 (lifecycle gate) |
| R21-F | stability | independent-process runs, anomaly tally |

## R22 channel facts (live scan + binary/ancestry audits, 2026-11-15)

| Channel | Newest Windows stack | MIOpen fix |
|---|---|---|
| multi-arch | torch 2.12.0+rocm7.14.1 | **NO** (frozen P14/P16 + R21-D1 runtime) |
| stable whl-next | torch 2.14.0+rocm10.1.0 | **NO** (P16 byte-identical re-audit) |
| **rc whl-next** | torch 2.15.0+rocm10.2.0rc2 | **NO — NEW PROOF**: DLL `3.6.2.8faffed0f` marker=0 AND `f0a5d266...8faffed0f` diverged (behind_by=92) — a post-merge build date yet pre-fix source |
| nightly whl-next | torch 2.16.0a0+rocm10.3.0a20261115 | audited in evidence/r21 (see R22 report) |
| **dev whl-next** | torch 2.16.0a0+git… | **SOURCE CONTAINS FIX** — `10.3.0.dev0+d318a1c3` → TheRock @ `d318a1c3` → rocm-libraries `7b33c3d9` → `f0a5d266` behind_by=0, ahead_by=606 |

## Verdicts (final, 2026-11-16)

- **R21_HARNESS_VALIDATED** — harness functional, backed by real gfx1100 runs (all 8 phases).
- **R22_CANDIDATE_VALIDATED (DEV channel)** — official dev wheels, fix PROVEN
  in source (behind_by=0) + binary (marker 2) + runtime (no-STL PASS, no
  shim); full clean gate suite green on gfx1100. Ceiling: DEV_CANDIDATE_PASS.
  **Stable-channel acceptance: BLOCKED_OFFICIAL_ARTIFACT.** gfx1151 + clean-Windows + ≥10-run matrix pending (runbook ready).
- **R23_DRAFT_READY** — developer docs prepared, NOT release-qualified
  (see docs/r23/).
