# CLAIMS AND EVIDENCE — release-closure phase (2026-11-14)

Legend: 状态 vocabulary PASS/FAIL/EXPECTED_FAIL/SKIP/BLOCKED/NOT_RUN/INCONCLUSIVE + provenance classes PROVEN/LIKELY/UNKNOWN.
Corrections from the P8 independent three-reviewer audit (2026-11-14) are applied in place; see `P8_INDEPENDENT_AUDIT.md`.

| # | Claim | Status | Class | Evidence |
|---|---|---|---|---|
| C1 | PR #13437 merged; TheRock #9359 merged; both recorded SHAs exact | PASS | PROVEN | gh api live re-check; `release-provenance/BASELINE_STATE.json` §upstream + `release-provenance/RELEASE_LINEAGE.md` (live re-verified in audit A) |
| C2 | TheRock #9359 bump target d875648 contains the fix | PASS | PROVEN | compare API ahead_by=2/behind_by=0 (live re-verified); recorded in `release-provenance/RELEASE_LINEAGE.md` |
| C3 | TheRock main submodule 2026-11-14 contains the fix | PASS | PROVEN | compare API 9ea8cfc5 ahead_by=1011/behind_by=0 (live re-verified); recorded in `release-provenance/RELEASE_LINEAGE.md` §TheRock |
| C4 | No official release/wheel contains the fix as of 2026-11-14 | PASS | PROVEN | tag dates + AMD index scan + pytorch.org scan + nightly index stale + marker=0 + behavioral EXPECTED_FAIL (all live re-verified in audit A; raw counts now in-repo `release-provenance/raw/miopen_dll_inventory_raw.json`) |
| C5 | ENV A is pristine official wheel; env B swap/restore discipline held | PASS | PROVEN | hash records e97891df/ed7c67a9 both directions (BINARY_PROVENANCE.json); 2026-11-14: zombies self-cleared, restore executed (ENVB_DLL_STATE.json), both env DLLs hash-verified e97891df at audit time |
| C6 | 16 training primitives numerically correct on HIP GPU, incl. hidden host STL | PASS | PROVEN | G1 matrix 16/16 ×3 ×2 modes + gtest ×3 + negative control (audit B recomputed all legs): `windows-training-validation/reports/G1_MATRIX_pm13437_merged_stl.json`, `G1_MATRIX_pm13437_official_stl.json`, `G1_MATRIX_nostl.json`, `raw/gtest_nostl_r1.log`, `raw/envA_nostl_neg.result.json` |
| C7 | BN running stats use unbiased estimator per PyTorch semantics (resolves the old caveat) | PASS | PROVEN | **persisted 2026-11-14 (audit fix B-F3)**: `raw/g1_bn_estimator_probe.json` — rv vs unbiased ref 6.812e-08 (reproduces the prose claim exactly), 45× closer to unbiased than biased ref |
| C8 | All 7 current Ultralytics 8.4.182 tasks complete T01–T15 lifecycle | PASS | PROVEN | g2_*.json ×7 (each 14/14 of 14 defined — harness defines no T02) = 98 PASS; canonical detect record restored from git `593160e` (audit fix B-F6) |
| C9 | Interrupt+resume + checkpoint semantics correct | PASS | PROVEN | t05/t09/t12 records in `windows-training-validation/raw/g2_detect_fp32.json` + `raw/g2_detect_fp32_resume.log` ("Resuming … from epoch 3 to 4"); final-strip semantics documented |
| C10 | Windows DataLoader works with workers 0/2/4 | PASS | PROVEN | `raw/g2_detect_fp32.json` (workers=0) + `raw/g2_detect_workers2.json` + `raw/g2_detect_workers4.json` — distinct runs verified |
| C11 | AMP "anomaly" = benign fp16 coordinate deltas + check_amp atol=0.5 design flaw, cache-state dependent | PASS | PROVEN | `raw/g3_amp_envB_patched.json` (5/5 PASS 0.233px) + `raw/g3_amp_envB_defaulthome.json` (0/5 FAIL 0.761px) deterministic flips; per-column range 0.0730–0.7606 px, conf ≤ 0.0043, cls=0 (audit-corrected numbers m1/m2) |
| C12 | AMP machinery (autocast/GradScaler) is healthy on this stack | PASS | PROVEN | `raw/g3_amp_envB_patched.json` §a_primitives (ENV B) + `raw/g3_amp_envA_official_defaulthome.json` (ENV A); scaler anneal trace `raw/g3_amp10_envA.json` |
| C13 | AMP machinery + ≥1 real update verified on the official wheel (10-epoch probe) | PASS | PROVEN (scoped) | g3_amp10_envA.json — scaler anneal 65536→8192, 3 of 4 steps overflow-skipped, **1 real update** (final epoch); fitness gains occurred at skipped-step epochs (BN running stats) — **demonstrates scaler semantics + anomaly-free completion, NOT weight-learning** (audit correction M5) |
| C14 | MIOpen solver-timing anomaly (gfx1151): `EvaluateInvokers elapsed <= 0` — **repeated on source-built 3.6.2 f0a5d266; rare-but-present on official 3.5.2** | PASS | PROVEN (re-scoped, audit M2) | 4× `raw/g2_pose_main.log:145-148` (ENV B, ed7c67a9 in-process); 1× aborted official-wheel attempt (`raw/scrambled_logs_20261114/g2_detect_envA_amptrack_main.log:150`, in-process binary unproven); 0× in clean official re-run (`g2_detect_envA_amptrack_rerun_*.log`); 0× in envB nostl probe logs. "Absent on official wheel" (original wording) was wrong |
| C15 | 30-epoch public-dataset training stable | PASS | PROVEN (re-labeled env) | g4_long_run_coco128.json (31 epochs, 0 exceptions, all finite 0.505→0.602) — ran on the **third environment** (miniconda base: python 3.13.13, ultralytics 8.4.174, torch 2.12.0+rocm7.14.0 pre-fix official wheel `74b4ee03`, host STL), **not ENV B** as previously labeled (audit M4); no in-process DLL probe (disclosed deviation) |
| C16 | Matched FP32-vs-AMP A/B measured with disclosed limits | PASS | PROVEN (re-labeled env) | g4_perf_ab_envA.json — 1.604× slower / VRAM −32.8% on tiny workload; same **third environment**, not ENV A (audit M4); "CSVs retained" claim was false — run dirs deleted by script (audit fix B-F9) |
| C17 | Quality comparison vs Linux ROCm reference | NOT_RUN | BLOCKED_HARDWARE | no Linux GPU machine |
| C18 | gfx1100/gfx1200 support | BLOCKED | BLOCKED_HARDWARE | tooling delivered, no results |
| C19 | Official release closure (GO-C full) | BLOCKED | BLOCKED_RELEASE | C4 |
| C20 | Upstream PRs created | NOT_RUN | — | mission boundary: Owner approval required; drafts only |

## Explicitly NOT claimed

- No AMD/Ultralytics official-support statement is made or implied.
- No cross-family GPU generalization.
- No bitwise-identity claims (fp32-vs-AMP trajectory differences are expected).
- No performance superiority claim for the fixed MIOpen (no valid pre-fix training baseline exists — the pre-fix wheel cannot run spatial-BN training at all).
- No weight-learning claim from the 10-epoch AMP probe (audit M5 — see C13).
- **Environment mapping of the suites (audit-corrected)**: all 7 full FP32 task lifecycles ran on ENV B (patched MIOpen, source-built). ENV A (official wheel) executed: G1 STL-visible matrix (PASS), the detect AMP-track lifecycle (**13/14 — t08 FAIL, deterministically reproduced on clean re-run 2026-11-14**; AMP effective), the G3 decomposition + 10-epoch probe, and the EXPECTED_FAIL negative control (exact signature). ENV A never ran hidden-STL legs except the negative control. **G4 (long run + perf A/B) ran on a third environment** — miniconda base: python 3.13.13, ultralytics 8.4.174, torch 2.12.0+rocm7.14.0 pre-fix official wheel (`74b4ee03`), host STL visible; no in-process DLL probes (disclosed deviation). ENV-B-amptrack lifecycle completed 14/14 with check_amp falling back to FP32 (cache-dependent, root-caused in G3).
