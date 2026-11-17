# G0 VERDICT — ROCm Release Provenance

Date: 2026-11-14 · Verdict: **BLOCKED_RELEASE** (source chain fully proven; no official release package contains the fix yet)

## PASS elements

| Gate item | Status | Evidence |
|---|---|---|
| G0.1 source chain | **PROVEN** | PR #13437 merged `f0a5d266` (gh api); TheRock #9359 merged `b0958085` bumping submodule to `d875648`; `d875648 ⊇ f0a5d266` (compare ahead_by=2/behind_by=0); TheRock main 2026-11-14 submodule `9ea8cfc5 ⊇ f0a5d266` (compare ahead_by=1011/behind_by=0) |
| G0.2 wheel chain | **PROVEN NEGATIVE** | AMD official index max = torch 2.12.0+rocm7.14.1 (marker=0, behavioral EXPECTED_FAIL); PyTorch.org has zero ROCm Windows wheels; TheRock nightlies (gfx1151) stale at 2026-06-12; no TheRock release after 2026-10-20 |
| G0.3 loaded-DLL proof | **PASS** | `probe_loaded_miopen.py` (Toolhelp in-process enumeration post-MIOpen-workload): ENV A loads `e97891df` (official, no fix), ENV B loads `ed7c67a9` (source-built f0a5d266, marker=2). Reports: `LOADED_DLL_REPORT.json`, raw JSONs |
| G0.4 baseline envs | **PASS (with category discipline)** | ENV A = pristine official wheel (re-hashed 2026-11-14, never modified). ENV B = disposable env with **source-built patched MIOpen**, swap/restore convention hash-verified both directions today. ENV B is never labeled "Official Stable Wheel" |

## BLOCKER (why not full PASS)

**BLOCKED_RELEASE** — the mission's G0 PASS condition ("存在可获得的发行包，并已充分证明它包含修复，且运行时加载了对应二进制") is not met: every obtainable official package predates the fix.

- What is needed: an official Windows wheel built from a TheRock release/branch whose rocm-libraries submodule contains `f0a5d266` (e.g., next SDK cut after 2026-10-20, a 7.14.2/10.2 backport, or resumed gfx1151 nightlies).
- Who: AMD/ROCm release engineering (Owner Action Required — external dependency, not actionable from this repo).
- Re-run on availability: the full G0 scan (RELEASE_LINEAGE §4 checklist) + G1/G2/G3 against the official wheel.

## Consequences for downstream gates

- G1/G2/G3 proceed in two environments: ENV A (official, **fix absent** — pre-fix behavior/EXPECTED_FAIL controls and wheel-reproduction of the AMP anomaly) and ENV B (source-built patched — validation of the fixed path).
- GO-C (Upstream Official-Ready) cannot reach full PASS until BLOCKED_RELEASE clears; GO-A/GO-B remain judgeable on ENV B evidence with explicit "source-built, not official wheel" labeling.
