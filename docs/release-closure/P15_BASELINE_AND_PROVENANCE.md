# P15.0 — Baseline and Provenance Freeze (2026-11-15)

Mission: P15 — Windows Radeon first-class YOLO training (official release × upstream quality × NVIDIA UX parity × independent acceptance).
This document re-verifies the P14 baseline against live remote state at P15 execution start. Historical raw data is preserved and immutable; no historical experimental conclusion is rewritten.

## 1. Repository state (live-verified 2026-11-15)

| Item | Value | Evidence |
|---|---|---|
| RCA branch | `work/windows-rocm-training-release-closure` | local fetch attempt (network-flaky, 3 retries) |
| Remote HEAD | `9c30131a8a24a274e67ec0734a4e2a32d3d7ab8d` (2026-11-15T02:44:42Z) | `gh api repos/AIwork4me/.../branches/...` |
| Local HEAD | `9c30131a…` — **identical to remote**, clean tree | `git log origin/...`, `git status` |
| Working tree | clean (no uncommitted changes) | `git status --short` (empty) |

No newer remote work exists; nothing is overwritten. Raw: `release-provenance/raw/p15_baseline/`.

## 2. Ultralytics PR #27198 (live state, not from memory)

| Field | Value |
|---|---|
| state / merged | **open / false** |
| head SHA | `090e37863ff698a15969e3414e77738fc6edc4f5` (unchanged from P14 tip) |
| commits / files | 4 commits, 2 files, +162/−7 |
| comments | 5 (no new human review since P14 session) |
| reviewDecision | none (REVIEW_REQUIRED semantics; `mergeable_state: blocked`) |
| updated_at | 2026-11-15T02:20:06Z |

Raw: `release-provenance/raw/p15_baseline/pr27198_state.json`. **GATE 2 remains IN_PROGRESS.**

## 3. Independent tester (issue #14)

- state: open; **comments: 0** (`issue14_state.json`). @LZ-QWQ has not responded.
- Verdict carried: **BLOCKED_INDEPENDENT_USER_TEST**. No credit granted to any unresponsive invitee.

## 4. Official wheel channels (re-scan 2026-11-15, headers + index, not version-number-only)

| Channel | Newest Windows wheel (cp313) | Change vs P14 |
|---|---|---|
| `stable.repo.amd.com/rocm/whl-next/` (redirects to `/rocm/pytorch/whl-next/`) | torch **2.14.0+rocm10.1.0** | **none** (index identical) |
| `repo.amd.com/rocm/whl-multi-arch/` | torch **2.12.0+rocm7.14.1** | **none** |

Silent-rebuild check on the decisive artifact `rocm_sdk_libraries-10.1.0-py3-none-win_amd64.whl`:

| Field | P14 record | Live HEAD probe | Match |
|---|---|---|---|
| Content-Length | 118,645,973 B | **118,645,973 B** | ✅ byte-identical size |
| Last-Modified | — | **Mon, 05 Oct 2026 09:19:46 GMT** | predates PR #13437 merge (2026-10-19) |
| P14 SHA256 | `0c34bafbb4aa626cc710d8b130bb314f591194c3d79eeb5892b755ea0be06159` | (size+date identity ⇒ same S3 object; full-hash re-download not re-run this session) | consistent |

MIOpen.dll inside that wheel (P14, immutable record): SHA256 `266d716b…c1429b4`, embedded version `3.6.1.39d8d603`, build commit `39d8d603` (2026-09-16) **< merge `f0a5d266` (2026-10-19)**; `miopen_initializer_list` marker 0 (merged ref = 2). Runtime legs (P14, preserved): A official-7.14.1 FAIL / B whl-next-10.1.0 FAIL / C merged-ref PASS — identical HIPRTC `type_traits` signature.

**Verdict carried: BLOCKED_RELEASE (dual-channel + runtime evidence, re-confirmed today).** No new material finding ⇒ **no new #15862 comment** (anti-spam rule honored; P14 comment 6887740468 remains the latest state of record).

## 5. Carried verdicts (from GO_NO_GO.md P14 addendum — unchanged today)

- GO-A: CONDITIONAL PASS (gfx1151 engineering correctness)
- GO-B: CONDITIONAL PASS (scope-labeled)
- GO-C: NO-GO (BLOCKED_RELEASE)
- GATE 1 ✅(gfx1151 only) · GATE 2 ⏳ IN_PROGRESS · GATE 3 ❌ BLOCKED_RELEASE · GATE 4 ❌ NOT_MET · GATE 5 ❌ not executed (NVIDIA hardware baseline unavailable so far) · GATE 6 ❌ BLOCKED_RUNNER

## 6. Host fingerprint (this session)

- GPU: AMD Radeon(TM) 8060S Graphics (gfx1151), driver 32.0.22032.6002; Windows build 10.0.26200 (`host_fingerprint.json`).
- P14-verified environments preserved: ENV A `pm13437_official` (official torch 2.12.0+rocm7.14.1, MIOpen `e97891df…`), ENV B `pm13437_merged` (source-built post-fix MIOpen `ed7c67a9…`), `yolo_amd` (official 7.14.0 wheel `74b4ee03…`), `p14_whlnext` (10.1.0 SDK `266d716b…`).

## 7. Security incident (still open — owner action required)

21 P9-era evidence files embedded a live **ZHIPU_API_KEY** and were pushed to the public RCA repo. HEAD is redacted (commit `e3398d4`, guard `scripts/scan_secrets.py`), but **git history still contains the blobs**. Rotation is an owner-side human action; P15 cannot verify it from inside the repository. Status: **OPEN — owner must rotate**; history rewrite remains an owner decision.

## 8. Root-cause ledger (frozen)

- Missing MIOpen FDB file alone does **not** cause invalid-kernel-file failures (P13 controlled experiment). Original root cause remains **UNRESOLVED** (3 archived candidates); P9 session crash evidence preserved unmodified.
- ENV B ghost-process / MIOpen.dll write-lock (err 32) persists (`p14_ghost_recheck.json`); ENV B still blocked until machine restart.
- AMP precheck silent-fallback design flaw fixed upstream in 8.4.197 (PR #26967); gfx1151 validation of the new check exists (`g3_checkamp84212_*`).

## 9. P15 execution-safety commitments

All §3 claims-policy prohibitions restated as binding for this mission: no weakened assertions, no silent CPU fallback, no FP32-as-AMP, no released-fix claim from a merged source PR, no GPU support inferred from package availability, no Linux/simulated evidence counted as Windows physical evidence, no maintainer-acceptance claim without GitHub confirmation.
