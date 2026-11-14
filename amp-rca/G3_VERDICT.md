# G3 VERDICT — AMP Root Cause Analysis

Date: 2026-11-14 · **Verdict: ROOT CAUSE FOUND (two layers, both benign-to-benign interaction); AMP verified working on the official wheel; no ROCm AMP numerical bug**

## Root cause (full chain in ROOT_CAUSE.md)

1. **Layer 1 — benign numerics**: FP32 vs autocast(fp16) inference differs by 0.15–0.76 **pixels** in box coordinates only (conf ≤ 0.004, class identical, same detection count, no NaN/Inf). Same-image FP32/AMP comparisons of detection *quality* are equivalent.
2. **Layer 2 — check design**: `ultralytics.utils.checks.check_amp` uses `torch.allclose(atol=0.5)` on raw pixel coordinates. Deltas > 0.5 px (observed 0.7606 px in one MIOpen cache state) → "AMP: checks failed … AMP will be disabled" → **silent FP32 fallback**. The outcome flips **solely on MIOpen cache state** (fresh home: 0.233 px PASS; default home: 0.761 px FAIL), deterministic within each state (5/5 repeats each).
3. **Layer 3 — kernel-selection instability (ENV B only)**: the source-built MIOpen 3.6.2 (f0a5d266) logs repeated `EvaluateInvokers … Invalid elapsed time … elapsed <= 0` (solver_finders.cpp:535) and picks fp16 conv solvers whose coordinate deltas exceed the 0.5 px tolerance in the default-cache state. The official wheel's MIOpen 3.5.2 shows no such errors and passes both contexts.
4. **Layer 4 — real AMP training verified (official wheel)**: 10-epoch run with autocast active — GradScaler anneals 65536→8192 while skipping overflow steps, then executes real updates (ΔΣ|θ|=-0.0063 at scale 8192); fitness 0.662→0.696. Textbook-correct scaler semantics.

## Deliverables

| Item | Path |
|---|---|
| Root cause analysis | `amp-rca/ROOT_CAUSE.md` |
| Minimal reproduction | `amp-rca/MINIMAL_REPRO.py` (per-column FP32-vs-AMP diff; runs in any env) |
| Full decomposition harness | `windows-training-validation/tests/g3_amp_rca.py` (primitives + precheck decomposition + real check_amp) |
| Real-AMP-training probe | `windows-training-validation/tests/g3_amp_training_10ep.py` |
| Raw evidence | `raw/g3_amp_envB_patched.json` (fresh home PASS), `raw/g3_amp_envB_defaulthome.json` (default home FAIL), `raw/g3_amp_envA_official_freshhome.json` + `raw/g3_amp_envA_official_defaulthome.json` (official wheel PASS both), `raw/g3_amp10_envA.json` (10-epoch real steps) |
| PRECISION_COMPARISON | `amp-rca/PRECISION_COMPARISON.csv` |
| Upstream drafts | `upstream-readiness/AMP_FIX_PR_DRAFT.md` (check_amp), `upstream-readiness/MIOPEN_EVALUATEINVOKERS_ISSUE_DRAFT.md` |

## Classification (mission G3.4)

- A (ROCm kernel bug): **No** for AMP numerics; **yes-adjacent** for the MIOpen 3.6.2 `EvaluateInvokers` timing anomaly (issue draft, not a fix — upstream code).
- B (PyTorch ROCm bug): **No** — autocast/GradScaler/dtype semantics correct.
- C (Ultralytics check issue): **Yes** — tolerance-vs-scale design flaw with silent-fallback consequence; minimal fix drafted (PR-C), cross-platform regression test included.
- D (Environment contamination): the trigger is MIOpen cache state — legitimate variable the check must be robust to, not contamination.

## Limitations

- FP32-vs-AMP deltas measured on one image (bus.jpg ×8, the exact precheck probe) at imgsz 256 — same conditions as the shipping check; quality-equivalence claims limited to detection count/class/conf behavior on this probe.
- ENV B AMP fallback depends on cache state — a property of the source-built 3.6.2 binary on this machine, not established for all future builds.
- The G2 4-epoch lifecycle's AMP-track "metric drift" was traced to BN running-stat updates with scaler-skipped weight updates — short-smoke artifact, documented in ROOT_CAUSE.md (no false AMP claims made from it).
