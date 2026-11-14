# G3 VERDICT — AMP Root Cause Analysis

Date: 2026-11-14 · **Verdict: ROOT CAUSE FOUND (two layers, both benign-to-benign interaction); AMP machinery verified on the official wheel (precheck + scaler anneal semantics + ≥1 real update); no ROCm AMP numerical bug**

## Root cause (full chain in ROOT_CAUSE.md)

1. **Layer 1 — benign numerics**: FP32 vs autocast(fp16) inference differs by 0.07–0.76 **pixels** in box coordinates only (archived per-column range 0.0730–0.7606; run-level maxima 0.233/0.761; conf ≤ 0.0043, class identical, same detection count, no NaN/Inf). Same-image FP32/AMP comparisons of detection *quality* are equivalent.
2. **Layer 2 — check design**: `ultralytics.utils.checks.check_amp` uses `torch.allclose(atol=0.5)` on raw pixel coordinates. Deltas > 0.5 px (observed 0.7606 px in one MIOpen cache state) → "AMP: checks failed … AMP will be disabled" → **silent FP32 fallback**. The outcome flips **solely on MIOpen cache state** (fresh home: 0.233 px PASS; default home: 0.761 px FAIL), deterministic within each state (5/5 repeats each).
3. **Layer 3 — kernel-selection instability (source-built 3.6.2 repeated; official 3.5.2 rare)**: the source-built MIOpen 3.6.2 (f0a5d266) logs repeated `EvaluateInvokers … Invalid elapsed time … elapsed <= 0` (solver_finders.cpp:535; 4× in `raw/g2_pose_main.log`) and picks fp16 conv solvers whose coordinate deltas exceed the 0.5 px tolerance in the default-cache state. **Re-scope (2026-11-14 audit M2)**: the official wheel's MIOpen 3.5.2 is *not* immune — one identical error was observed in an aborted official-wheel amptrack attempt (`raw/scrambled_logs_20261114/g2_detect_envA_amptrack_main.log:150`, in-process binary unproven for that aborted attempt), and 0 occurrences in the clean official-wheel re-run (`g2_detect_envA_amptrack_rerun_*.log`) — so the faulty condition exists in both binaries; what is ENV-B-specific is the delta magnitude *crossing the 0.5 px threshold* in the default-cache state.
4. **Layer 4 — real AMP training probe (official wheel)**: 10-epoch run with autocast active — GradScaler anneals 65536→8192 while skipping overflow steps (3 of 4 step opportunities skipped), then executes a real update (ΔΣ|θ|=-0.0063 at scale 8192, final epoch); fitness 0.662→0.696→0.689. **Interpretation corrected (audit M5)**: the fitness gains occurred at *skipped-step* epochs (BN running-stat updates, the same mechanism as the 4-epoch drift), and fitness *decreased* after the only real weight update — this probe demonstrates correct scaler anneal semantics + anomaly-free AMP completion + ≥1 real update, **not** demonstrated weight-learning. Textbook-correct scaler anneal semantics.

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
