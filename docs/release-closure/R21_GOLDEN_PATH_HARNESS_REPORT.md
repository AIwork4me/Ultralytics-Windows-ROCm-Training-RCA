# R21/R22-prep/R23-prep — Windows Golden Path Harness (2026-11-15/16)

**Machine:** AMD Radeon RX 7900 XTX (gfx1100) · Windows 11 build 26300 · driver 32.0.21030.2001
**Branch:** `feature/r21-windows-golden-path` (base `e81a89e`, frozen from `work/windows-rocm-training-release-closure`)
**Workspace:** `C:\RadeonYOLO\` (isolated; P17/P18/P19 untouched)

## TL;DR

1. **R21_HARNESS_VALIDATED** — the `windows-golden-path/` toolkit exists, its
   CPU contract tests pass (28/28), the repo verifier stays 575/0, and every
   gate has been exercised on physical gfx1100 hardware, including two real
   PS 5.1 portability bugs found and fixed by the validation itself.
2. **The official-channel picture changed tonight.** A five-channel scan
   (multi-arch/stable/rc/nightly/dev — rc/nightly/dev were never scanned
   before) found: **rc 10.2.0rc2 is still PRE-FIX** (proven by ancestry
   `behind_by=92` + marker 0 — a post-merge build date yet pre-merge source),
   while **nightly libraries and the whole dev channel are POST-FIX** (marker
   2 + `behind_by=0` lineage to `f0a5d266`).
3. **First official-channel post-fix no-STL runtime PASS on Windows gfx1100**:
   the dev stack (`rocm-sdk-libraries 10.3.0.dev0+ff576965`) passed
   BatchNorm2d(100)@(20,100,35,45) with **no shim, cold cache,
   VCToolsInstallDir redirect** → `OFFICIAL_CANDIDATE_PASS` (gate C). Full
   dev-candidate gate suite run (see §R22).
4. **Stable-channel acceptance remains BLOCKED_OFFICIAL_ARTIFACT** — no stable
   wheel carries the fix; `R22_CANDIDATE_VALIDATED` at DEV level only.
5. R23 developer documentation drafted (`docs/r23/`) with verified install
   commands — **R23_DRAFT_READY**, not release-qualified.

## R21 — harness

Delivered `windows-golden-path/`: `run-golden-path.ps1` (5 explicit modes,
fail-closed classification banners), 13 scripts, `acceptance-contract.json`
(G0–G9 machine-checkable), `compatibility-matrix.yaml`, hash-pinned
`requirements-lock/`, 28 CPU-only contract tests, docs (architecture /
troubleshooting / release-checklist / R22 runbook / R23 drafts).

Physical gfx1100 results (engineering-reference stack: official 7.14.1 wheels
+ disclosed HIPRTC shim; ultralytics 8.4.214 released wheel in a fresh venv):

| Gate | Result |
|---|---|
| A provenance | fail-closed → ENGINEERING_REFERENCE; loaded DLL `e97891df…` = `3.5.2.cd957402`, marker 0; shim auto-detected |
| A2 GPU gates | **PASS 9/9** incl. `torchvision.ops.nms` (device wheel present) |
| D1 no-STL (no shim) | **OFFICIAL_PRE_FIX_EXPECTED_FAIL** — exact #3956 signature (`HIPRTC_ERROR_COMPILATION` → `'type_traits' file not found` → `miopenStatusUnknownError`), cold cache |
| D2 no-STL (shim) | **ENGINEERING_REFERENCE_PASS** — same wheel bytes, only the shim differs |
| E1 exact CLI | **PASS** — `yolo train model=yolo26n.pt data=coco8.yaml epochs=1 device=-1`, exit 0, GPU via device=-1, AMP passed, val mAP50 0.943, last/best.pt SHA256'd |
| E2 optimizer | **PASS** — 183 steps; 361/366 tensors changed (max |Δ| 0.295); scaler 8192→128, 5 per-step backoffs; forward autocast 192/192; buffers excluded; supplementary-harness disclosed |
| E3 interrupt→resume | **PASS** — killed after epoch checkpoint (rc≠0); checkpoint optimizer-state verified pre-launch; NEW process resume=True ("Resuming…" logged); final epoch reached; best.pt GPU inference in third process |
| F stability | **PASS 3/3** independent processes, zero anomaly families |

Harness bugs found & fixed by this validation (PS 5.1.26100: `WaitForExit`
ms-units; `Start-Process -PassThou`+redirect loses `ExitCode`; native-arg
quote mangling → JSON via files; `-Include` needs `\*`; cp936 decode →
explicit UTF-8; resume-race vs 1.2s epochs → exact-row interrupt trigger +
resumability pre-check refusing silent fresh-training fallback).

## R22 — official wheel acceptance (prepared + candidate-level run)

Channel matrix (live scan + binary + ancestry proofs, all 2026-11-15):

| Channel | Newest Windows set | Fix | Proof |
|---|---|---|---|
| multi-arch | 2.12.0+rocm7.14.1 | ❌ | P14/P16 frozen + D1 live |
| stable | 2.14.0+rocm10.1.0 | ❌ | P16 byte-identical |
| rc | 2.15.0+rocm10.2.0rc2 | ❌ **new** | wheel `ffbf6c77…`; DLL `3.6.2.8faffed0f` marker 0; compare diverged `behind_by=92` |
| nightly | 10.3.0a20261115 libraries | ✅ | DLL `3.6.3.9ea8cfc5` marker 2; `behind_by=0` (re-verified) — but gfx1100 device wheels not listed |
| dev | 10.3.0.dev0+`<TheRock sha>` | ✅ | installed `+ff576965` → submodule `4e7d93e3` `behind_by=0`; full gfx1100 device set |

Dev-candidate physical run (torch 2.15.0+gitf6cd88cb · HIP 7.18 · ultralytics
8.4.214), gates run BOTH shim-assisted and shim-stripped; the clean
(shim removed from the environment) set is the authoritative one:

| Gate (clean, no shim) | Result | Record |
|---|---|---|
| G0 provenance | **OFFICIAL_CANDIDATE** (marker 2, DLL `3.6.3.4e7d93e3`, ancestry behind_by=0, zero workarounds) | `r22cA2_provenance_clean.json` |
| G1 no-STL | **OFFICIAL_CANDIDATE_PASS** — cold cache, VCToolsInstallDir redirect, no shim | `r22cC_nostl.json` |
| G2 GPU gates | **PASS 9/9** incl. torchvision nms via dev device wheel | `r22cB2_torch_gates_clean.json` |
| G3 exact CLI | **PASS** exit 0, GPU, AMP, checkpoints hashed | `r22cD2_train_cli_clean.json` |
| G4 optimizer | **PASS** (steps, named-parameter deltas, per-step scaler history) | `r22cE2_optimizer_clean.json` |
| G5 interrupt→resume→infer | **PASS** (resumability verified pre-launch; epoch continuity via csv epoch column) | `r22cF2_resume_clean.json` |
| G8 subset | warm 3/3 + cold 2/2 independent processes, zero anomaly families | `r22cG_stability.json`, `r22cG3_stability_clean_cold.json` |

**Verdict: `R22_CANDIDATE_VALIDATED` at DEV-channel level** (ceiling
DEV_CANDIDATE_PASS — a dev wheel can never satisfy stable acceptance).
NOT earned tonight: G7 gfx1151 (runner portable, run unchanged on the 8060S),
G9 clean-Windows (BLOCKED_INFRASTRUCTURE on this dev host), full ≥10-run
reliability matrix per arch, and therefore any OFFICIAL_STABLE claim —
stable acceptance stays **BLOCKED_OFFICIAL_ARTIFACT**. R22 deliverables:
watchlist, gate matrix, acceptance runbook (portable gfx1100+gfx1151),
`resolve_package_set.py` / `install_official.ps1` lock+hash-verified install
path.

Known label caveat: process-level `runtime_class` in the clean records
B2/D2/E2/F2/G3 predates the channel/marker-aware classification patch
(applied after the runs — see git history); those records carry no workaround
flags and their suite classification is governed by the provenance record A2
(OFFICIAL_CANDIDATE). Records written by future runs classify in-process.

## R23 — developer experience (draft)

`docs/r23/`: README guide, INSTALL_WINDOWS, COMPATIBILITY, TROUBLESHOOTING,
VALIDATION_RESULTS, quickstart.ps1 (verified commands, blocker banner),
expected-cli-output.txt (real log), RELEASE_SUMMARY (community draft).
gfx1100/gfx1151 differ only in device-wheel names. Independent-developer
validation: **PENDING_EXTERNAL_VALIDATION**. No-workaround guide withheld
until OFFICIAL_STABLE_PASS.

## Honest boundaries

- No gfx1151 execution tonight (portable runner ready; same bytes on 8060S)
- G9 = BLOCKED_INFRASTRUCTURE on this dev host (HOST_REUSE_FRESH_VENV only)
- Reliability matrix at R21 scale (3 warm/2 cold), not the full R22 ≥10/arch
- COCO8/coco128 are smoke datasets; mAP not a quality benchmark
- Historical P14–P19B evidence untouched; verifier 575/0 after all changes
