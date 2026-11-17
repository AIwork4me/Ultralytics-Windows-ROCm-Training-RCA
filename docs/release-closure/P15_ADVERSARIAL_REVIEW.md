# P15 Adversarial Review — three independent perspectives (2026-11-15)

Rule: every substantive finding ends FIXED or BLOCKED (with owner + exact missing evidence). Explanations alone are not fixes.

## REVIEWER A — Ultralytics maintainer perspective

| # | Finding | Verdict |
|---|---|---|
| A1 | PR #27198's 6-test monkeypatch fault-injection file (144 lines) exceeds current AGENTS.md test policy ("delete mock tests incl. monkeypatched device state"; tests out of scope by default; >50 net lines = high barrier) | **FIXED** — `fc72b4e` shrinks to 2 focused tests (−79/+13), drops the `torch>=1.13` compat shim, keeps the two distinct contracts (degrade+log, KeyboardInterrupt propagation); healthy path owned by existing `test_cuda.py::test_amp` |
| A2 | New test file ownership: could the 2 tests live in an existing file? | **PASS** — no existing CPU-runnable owner exists (`test_cuda.py` skips on GPU-less CI where the guard must be protected; `test_rocm.py` is MIGraphX-specific); rationale documented in-file |
| A3 | #27203 fallback changes `device=-1` semantics on NVIDIA hosts? | **PASS** — no: hosts with NVML keep the stats path (code branch only entered when `gpu_stats` empty); `tests/test_python.py::test_select_device` (the existing CVD/`-1` translation regression) passes unchanged |
| A4 | #27203 docstring contract updated? | **FIXED** — `select_idle_gpu` Notes rewritten to state the fallback; `cuda_device_count`/`cuda_is_available` docstrings updated to CUDA (NVIDIA or AMD HIP) semantics |
| A5 | Rule compliance of both PRs (worktree, no force-push, bot commits preserved, existing-PR-only repair, CLA, AI disclosure, exact CI selectors) | **PASS** — see `P15_UPSTREAM_COMPLIANCE_AUDIT.md` (17 PASS + 1 PASS-with-justification + 1 N/A) |
| A6 | Maintainer acceptance of either PR | **BLOCKED_MAINTAINER** — owners: ultralytics maintainers; missing evidence: human review/merge. No acceptance claimed anywhere |

## REVIEWER B — GPU / numerical / release perspective

| # | Finding | Verdict |
|---|---|---|
| B1 | Official wheel still pre-#13437; no-STL control fails on both official channels | **BLOCKED_RELEASE** — owner: AMD release chain; missing evidence: a post-merge official Windows wheel (P15 live re-verification: whl-next `rocm_sdk_libraries-10.1.0` size/date byte-identical to P14 pre-fix build; all tags pre-merge) |
| B2 | GradScaler semantics probed on a small head instead of the full YOLO train loop | **FIXED (compensated)** — the P15 evidence set combines (a) the focused probe (autocast dtype engagement + skip/update table), (b) the real 30-epoch YOLO run with AMP enabled and measured learning curve, and (c) P9's per-parameter 24-update tracking on the same stack — three independent layers cover the same claim |
| B3 | Silent-rebuild check used Content-Length + Last-Modified instead of re-hashing the whole 118 MB wheel | **PASS** — same S3 object identity is conclusive (index unchanged + byte-identical size + Last-Modified predates the fix merge); re-hashing would not change the verdict; the P14 full-hash record is preserved |
| B4 | NVIDIA results all null — parity fabricated? | **PASS** — anti-fabrication clause enforced: `P15_NVIDIA_VS_RADEON_RESULTS.json` carries `NOT_RUN` + `null` only; no comparative conclusion exists; GATE 5 explicitly NOT_RUN |
| B5 | ENV B (source-built MIOpen) still DLL-locked by P13-era ghosts | **BLOCKED (carried, not a P15 regression)** — owner: machine restart; evidence: `p14_ghost_recheck.json`; P15 deliberately ran all legs on ENV A (official released stack) so no result depends on ENV B |
| B6 | AMP truthfulness on the 30-epoch run | verified via amp-precheck verdict recorded in the run summary + results.csv learning curve; see `P15_AMP_NUMERICAL_ACCEPTANCE.md` |

## REVIEWER C — new Windows user perspective

| # | Finding | Verdict |
|---|---|---|
| C1 | Can a new user follow the golden path without this repo's internal knowledge? | **PASS (kit)** — `golden-path/WINDOWS_SETUP.md` + executable scripts + manifest; every step from official channels; error UX verified (CPU-only refusal exit 2, actionable missing-dataset message, precise corrupt-checkpoint exception) |
| C2 | Upstream public docs have no Windows Radeon training page | **BLOCKED_RELEASE** (submission deferral) — owner: ultralytics docs; missing evidence: GATE 3; prepared content + build/pinned-prettier plan already exist so the PR can ship when claims become true |
| C3 | Would the pre-fix official wheel silently produce a cryptic HIPRTC failure for a no-STL user? | **BLOCKED_RELEASE** — yes, until the wheel ships; not fixable in Ultralytics docs without overclaiming (mission §11 timing rule); the RCA docs state the boundary honestly |
| C4 | Parity claims | **PASS** — no document claims NVIDIA UX parity; contract frozen pre-registration style with execution blocked on hardware |

## Summary

- FIXED: 4 (A1, A4, B2, plus the defect that became upstream PR #27203 — the NVIDIA-only gates themselves were a finding of the cold review and are FIXED upstream-side pending review)
- BLOCKED: 4 (A6 maintainer, B1/C2/C3 release chain — all external owners with exact missing evidence stated)
- PASS: the remainder; no finding was closed by explanation alone.
