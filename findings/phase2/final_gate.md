# Phase-2 Final Gate (Gate 46)

Date: 2026-10-07. Branch `rca/windows-gfx1151-rocm714-phase2`.

## Independent review panel (Gate 45 + Gates 20/23/44 audits)

| Review | Verdict | Disposition |
|---|---|---|
| Gate-20 handoff audit | CONDITIONAL PASS | 4 amendments applied to `phase1_handoff_review.md` (citations, external leads, methodology constraints, caveats) |
| Gate-23 clean-env audit | CONDITIONAL PASS | 4 amendments applied (provenance headers via `21_clean_repro.ps1`, wording subset/caveats, gitattributes custody, pip-check row) |
| Gate-44 security audit | CONDITIONAL PASS | All conditions remediated: Phase-1 `bn_variants_results.json` restored from `8e5e336` + `evidence/SHA256SUMS.txt` verified all-OK; 72 `.bc` bitcode files removed + `*.bc` ignored; LF-normalized blobs renormalized byte-exact; manifest regenerated skipping gitignored files |
| Gate-45 Reviewer A (ROCm/MIOpen) | **PASS** | Non-blocking findings addressed: `STD_INVENTORY.txt` relabeled tree-wide; `miopen_utility.hpp` attribution split to `b514736610`; inner-macro rename noted; A-3 "no MSVC" wording corrected; `hiprtcVersion()==9.0` footnote accepted |
| Gate-45 Reviewer B (falsification) | **PASS** | "No alternative explanation survives" (cache, MSVC-side-effects, shim-leakage, DLL-patch soundness, overclaim checks all attacked and failed) |
| Gate-45 Reviewer C (maintainer simulation) | CONDITIONAL PASS | RCA accepted as upstream-issue-grade; candidate-fix PR correctly judged NOT yet submittable. Blocker #1 (unvalidated patch) addressed post-review: candidate-B v2 with correct gate semantics now preprocess+compile+GPU-execute validated (`candidateB/candidate_b_v2_validation.txt`). Remaining blockers (Linux HIP≥7 regression runs, non-BN std-using RTC kernels coverage, version matrix) are Phase-3/PR-prep items recorded in `docs/PHASE2_NEXT_STEPS.md` — by design, Phase 2 stops before PR work |

## Gate checklist (20–46)

| Gate | Status |
|---|---|
| 20 handoff verification | PASS (audit amended) |
| 21 real environment | PASS — ENV-B determined with evidence |
| 22 clean environment | PASS — SHA256-identical curated clone + isolation caveats documented |
| 23 clean-env reproduction | PASS — branch A (identical signature), P2-H1 falsified |
| 24 standalone HIPRTC | PASS — 6-probe matrix + executing control |
| 25 include discovery | PASS — env + clang search captured (proxy labeled) |
| 26 MSVC discovery | PASS — MSVC_ABSENT |
| 27 MSVC A/B | PASS — pattern 1 (all three arms) |
| 28 H10 vs H11/H12-P2 | PASS — LEVEL-3 two-layer decision |
| 29 upstream archaeology | PASS — ce14dab3 + b514736610 + hiprtc/clr sources archived |
| 30 candidates enumerated | PASS — A/B/C/D evaluated |
| 31 STL inventory | PASS — 13-file closure, 5 traits, only `<type_traits>` |
| 32 candidate A/B experiments | PASS — A validated (3 ways), naive D falsified, DLL restored+verified, B v2 compile+exec validated |
| 33 regression matrix | PASS — 8/8 |
| 34 numerical correctness | PASS — ≤7.2e-7 vs CPU |
| 35 YOLO closure | PASS — amp=False + default, full success criteria |
| 36 fresh-process | PASS — scrubbed env, BN+YOLO |
| 37 reboot persistence | **NOT TESTED** (impossible in-session; no claim made) |
| 38 cross-version | PASS — local/external separated, defect window derived |
| 39 LEVEL-3 conclusion | PASS — `docs/PHASE2_LEVEL3_RCA.md`, LEVEL 3 PROVEN |
| 40 hypotheses | PASS — P2-H1..H8 dispositioned |
| 41 claims ledger | PASS — P2-C001..C026 (post-review corrections applied) |
| 42 reproducibility bundle | PASS — `scripts/phase2/` parameterized runners |
| 43 artifact integrity | PASS — manifest + SHA256SUMS regenerated post-remediation; Phase-1 hashes verified intact |
| 44 security/hygiene | CONDITIONAL PASS → remediated (above) |
| 45 review panel | 2× PASS + 1× CONDITIONAL PASS (RCA-grade; PR-prep blockers documented) |
| 46 decision package | this file + `phase2_conclusion.json` + `docs/PHASE2_SUMMARY.md` + `docs/PHASE2_NEXT_STEPS.md` |

## Upstream actions taken

**NONE.** No PR, no issue, no comment, no push to any ROCm upstream.
`pr_created: false`. Evidence commits go only to
`AIwork4me/Ultralytics-Windows-ROCm-Training-RCA` (permitted by the brief).

**Final gate result: PHASE 2 CLOSED — LEVEL 3 PROVEN, YOLO training closed
end-to-end, review panel satisfied, STOPPED BEFORE UPSTREAM SUBMISSION.**
