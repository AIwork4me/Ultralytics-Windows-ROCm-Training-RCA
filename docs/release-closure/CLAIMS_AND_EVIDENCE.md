# CLAIMS AND EVIDENCE — release-closure phase (2026-11-14)

Legend: 状态 vocabulary PASS/FAIL/EXPECTED_FAIL/SKIP/BLOCKED/NOT_RUN/INCONCLUSIVE + provenance classes PROVEN/LIKELY/UNKNOWN.

| # | Claim | Status | Class | Evidence |
|---|---|---|---|---|
| C1 | PR #13437 merged; TheRock #9359 merged; both recorded SHAs exact | PASS | PROVEN | gh api live re-check (BASELINE_STATE.json §upstream) |
| C2 | TheRock #9359 bump target d875648 contains the fix | PASS | PROVEN | compare API ahead_by=2/behind_by=0 |
| C3 | TheRock main submodule 2026-11-14 contains the fix | PASS | PROVEN | compare API 9ea8cfc5 ahead_by=1011/behind_by=0 |
| C4 | No official release/wheel contains the fix as of 2026-11-14 | PASS | PROVEN | tag dates + AMD index scan + pytorch.org scan + nightly index stale + marker=0 + behavioral EXPECTED_FAIL |
| C5 | ENV A is pristine official wheel; env B swap/restore discipline held | PASS | PROVEN | hash records e97891df/ed7c67a9 both directions (BINARY_PROVENANCE.json) |
| C6 | 16 training primitives numerically correct on HIP GPU, incl. hidden host STL | PASS | PROVEN | G1 matrix 16/16 ×3 ×2 modes + gtest ×3 + negative control |
| C7 | BN running stats use unbiased estimator per PyTorch semantics (resolves the old caveat) | PASS | PROVEN | g1_bn_estimator_probe: 6.8e-08 max delta vs float64 unbiased ref |
| C8 | All 7 current Ultralytics 8.4.182 tasks complete T01–T15 lifecycle | PASS | PROVEN | g2_*.json ×7 (each 14/14) + per-task loaded-DLL probes |
| C9 | Interrupt+resume + checkpoint semantics correct | PASS | PROVEN | t05/t09/t12 records; final-strip semantics documented |
| C10 | Windows DataLoader works with workers 0/2/4 | PASS | PROVEN | g2_detect_{fp32,workers2,workers4}.json |
| C11 | AMP "anomaly" = benign fp16 coordinate deltas + check_amp atol=0.5 design flaw, cache-state dependent | PASS | PROVEN | g3_amp_* JSONs; per-column MINIMAL_REPRO; deterministic 5/5 flips |
| C12 | AMP machinery (autocast/GradScaler) is healthy on this stack | PASS | PROVEN | g3 section A both envs; 10-epoch anneal trace |
| C13 | Real AMP training works on the official wheel | PASS | PROVEN | g3_amp10_envA.json (scaler anneal + real updates + fitness ↑) |
| C14 | MIOpen 3.6.2 source-built: EvaluateInvokers negative-timing anomaly (gfx1151) | PASS | PROVEN | error lines in envB logs; absent on official wheel; upstream draft filed |
| C15 | 30-epoch public-dataset training stable | PASS | PROVEN | g4_long_run_coco128.json (31 epochs, 0 exceptions) |
| C16 | Matched FP32-vs-AMP A/B measured with disclosed limits | PASS | PROVEN | g4_perf_ab_envA.json (AMP slower 1.60× on tiny workload; VRAM −33%) |
| C17 | Quality comparison vs Linux ROCm reference | NOT_RUN | BLOCKED_HARDWARE | no Linux GPU machine |
| C18 | gfx1100/gfx1200 support | BLOCKED | BLOCKED_HARDWARE | tooling delivered, no results |
| C19 | Official release closure (GO-C full) | BLOCKED | BLOCKED_RELEASE | C4 |
| C20 | Upstream PRs created | NOT_RUN | — | mission boundary: Owner approval required; drafts only |

## Explicitly NOT claimed

- No AMD/Ultralytics official-support statement is made or implied.
- No cross-family GPU generalization.
- No bitwise-identity claims (fp32-vs-AMP trajectory differences are expected).
- No performance superiority claim for the fixed MIOpen (no valid pre-fix training baseline exists — the pre-fix wheel cannot run spatial-BN training at all).
- **Environment mapping of the G2 suite**: all 7 full task lifecycles ran on ENV B (patched MIOpen, source-built). ENV A (official wheel) executed: G1 STL-visible matrix (PASS — host STL visible makes the pre-fix wheel work), the detect AMP-track lifecycle (14/14, AMP effective), the G3 decomposition, and the G4 perf A/B. ENV A never ran hidden-STL legs except the negative control (EXPECTED_FAIL, exact signature).
