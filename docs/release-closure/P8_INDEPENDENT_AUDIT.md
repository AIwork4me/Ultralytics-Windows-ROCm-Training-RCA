# P8 INDEPENDENT AUDIT — three-reviewer adversarial re-verification (2026-11-14 evening)

**Method**: three independent read-only reviewers ran in parallel, each auditing a different
perspective against the **raw evidence** (never trusting the summary docs), recomputing
numbers where feasible: **A = release provenance & binary evidence (C1–C5)**, **B = technical
validation evidence G1/G2/G4 (C6–C10, C15, C16)**, **C = AMP RCA + GO/NO-GO consistency +
upstream drafts (C11–C14, GO-A/B/C, verifier, drafts)**. No reviewer saw another's output.
This re-executes the P8 audit cancelled in the original session (HANDOFF pending item #1).

**Verdicts**: `AUDIT-A: PASS-WITH-FINDINGS` · `AUDIT-B: PASS-WITH-FINDINGS` · `AUDIT-C: PASS-WITH-FINDINGS`
**Consolidated**: claims ledger stands with corrections applied in place (see
`CLAIMS_AND_EVIDENCE.md`); 11 MAJOR findings, all dispositioned below; 0 blockers to the
existing GO-A/GO-B conditional structure — **GO-C NO-GO unchanged** (external blocker).

## Claim-level outcome (post-audit)

| Claim | Audit verdict | Post-disposition |
|---|---|---|
| C1–C4 upstream/release lineage | VERIFIED (A: live gh api + live index re-checks + marker recompute + behavioral EXPECTED_FAIL) | stands |
| C5 binary/swap discipline | VERIFIED (A: 7 DLL sha256 recomputed, all 21 raw loaded-DLL records aggregated, zero cross-contamination) | stands |
| C6 G1 16-primitive matrix | VERIFIED (B: 16/16 ×3 ×2 + gtest 6/6 + 4-element negative-control signature verbatim) | stands |
| C7 BN unbiased estimator | DISCREPANCY (B: 6.8e-08 was prose-only) | **FIXED** — deterministic probe re-run, evidence persisted `raw/g1_bn_estimator_probe.json` (6.812e-08, 45× closer to unbiased than biased) |
| C8 7×14=98 lifecycle PASS | VERIFIED (B: recomputed 98 exactly; canonical detect record restored from git `593160e`) | stands (restored record re-committed) |
| C9/C10 resume + workers | VERIFIED (B: resume-from-checkpoint log evidence; distinct workers runs) | stands |
| C11 flip experiment | VERIFIED (C: 4 JSONs × 5 repeats recomputed; harness replicates exact installed check_amp semantics) | numbers corrected in docs (m1/m2) |
| C12 AMP machinery | VERIFIED (C: section A all 4 JSONs) | stands |
| C13 AMP 10-epoch probe | VERIFIED file-level; **interpretation overstated** (C/M5) | **REWRITTEN** — "scaler anneal semantics + anomaly-free completion + ≥1 real update", NOT weight-learning (3/4 steps skipped; fitness gains at skipped-step epochs; fitness dropped after the only real update) |
| C14 EvaluateInvokers anomaly | DISCREPANCY (B-F5 + C-M2: 1 occurrence in an aborted official-wheel attempt log contradicts "absent on official wheel") | **RE-SCOPED** — repeated on source-built 3.6.2 (4× `g2_pose_main.log`), rare-but-present on official 3.5.2 (1× aborted attempt, in-process binary unproven; **0× in clean official re-run**), ENV-B-specific is *crossing* the 0.5px threshold; strengthens the upstream issue |
| C15/C16 G4 long run + A/B | DISCREPANCY (A-F1 + B-F1 + C-M4: ran on a **third environment** — miniconda base, python 3.13.13, ultralytics 8.4.174, torch 2.12.0+**rocm7.14.0** pre-fix official wheel `74b4ee03`; NOT ENV A/B; numbers themselves all recomputed-correct: 31 epochs/0 exceptions, 1.604×, −32.8%) | **RE-LABELED** everywhere (LONG_RUN_REPORT, PERFORMANCE_REPORT, METRICS.csv, CLAIMS, GO-A/GO-C rows, FINAL_REPORT §D/§E); G4 re-run on ENV A/B with probes = new pending item |
| GO-A / GO-B / GO-C | GO-A/GO-B VERIFIED (conditional structure honest); GO-C NO-GO right but one row false ("two available environments" for G4) | rows corrected; GO-C verdict unchanged |

## Findings ledger & dispositions

### MAJOR (11 — all dispositioned)

| ID | Finding | Disposition |
|---|---|---|
| A-F1 = B-F1 = C-M4 | G4 evidence ran on undocumented third environment, mislabeled as ENV A/B in 4+ docs; no loaded-DLL probes | Relabeled truthfully everywhere (see claim table); G4 scripts' missing provenance capture noted; ENV A/B re-run recorded as pending item |
| B-F2 | ENV A AMP lifecycle is **13/14** (t08 FAIL: `max_param_abs_sum_delta=0.0` @ lr 4.006e-05), docs claimed 14/14 | Docs corrected (G2_VERDICT, CLAIMS §34, FINAL_REPORT). **Clean re-run 2026-11-14: t08 FAIL deterministically reproduced** (identical values, `raw/g2_detect_envA_amptrack_rerun.json`); mechanism hypothesis (GradScaler overflow-skip) documented as plausible-unproven |
| B-F3 | C7's 6.8e-08 existed only in prose | Fixed: probe re-run + persisted (`raw/g1_bn_estimator_probe.json`), exact reproduction |
| B-F4 | Four detect logs scrambled/misnamed (runner's task-keyed filenames); ENV-B detect fp32 + amptrack main logs lost | Originals preserved verbatim in `raw/scrambled_logs_20261114/`; forensic mapping in `raw/README.md`; naming limitation documented in G2_VERDICT |
| B-F5 = C-M2 | EvaluateInvokers error present in an ENV-A amptrack attempt log — contradicts C14 "absent on official wheel" | Re-scoped (see C14 row); clean official re-run adds 0-occurrence counter-evidence; issue draft corrected accordingly |
| B-F3' = C-M3 | Issue draft cited wrong logs (`envB_nostl_rep*.probe.log` contain no errors) and denied official-wheel occurrence + claimed "≤~0.23px" | Draft corrected: cites `g2_pose_main.log`, discloses the official-wheel occurrence, honest delta statement |
| C-M1 | ROOT_CAUSE TL;DR claimed official-wheel deltas "≤ ~0.23 px in both cache states" — actual 0.264/0.423 | Corrected (both below 0.5 threshold — argument unchanged, numbers honest) |
| C-M5 | "Genuinely learns under AMP" overstated in 4 docs/drafts | Rewritten to honest scope (see C13) in ROOT_CAUSE, G3_VERDICT, MAINTAINER_CHECKLIST row 8, AMP_FIX_PR_DRAFT, FINAL_REPORT |
| A-F2 | ENVB_DLL_STATE.json held only latest action | Script now appends a transition history chain (swap-in/restore runs of 2026-11-14 will chain on next use; earlier records preserved in git) |
| A-F3 = C-m5(part) | Verifier glob `g3_amp_*` missed `g3_amp10_envA.json` (sole C13 evidence); no g4 coverage | Verifier extended: `g3_amp*.json` + `g4_*.json` globs with tiered provenance checks; docstring corrected; contract grew 184→218 checks, exit 0 |
| B-F6 | Canonical `g2_detect_fp32.json` deleted from working tree (survived only in git) | Restored from `593160e` (14/14, `ed7c67a9`), now committed; note: the R1 re-run briefly overwrote the first restore (runner reuses the task-keyed path) — restored again before commit |

### MINOR (9 — all dispositioned)

- **m1** conf "≤0.004" → "≤0.0043" (ROOT_CAUSE, G3_VERDICT, PR-C, FINAL_REPORT, HANDOFF). ✅
- **m2** "0.15–0.76 px" → "0.07–0.76 px (per-column 0.0730–0.7606; run-level maxima 0.233/0.761)". ✅
- **m3** nonexistent `G1_MATRIX_pm13437_merged_nostl.json` citations → `G1_MATRIX_nostl.json` (G1_VERDICT, MAINTAINER_CHECKLIST). ✅
- **m4** "machine-checked/enforced" overstated → softened in GO_NO_GO (pattern scan = screening aid; audit is the line-by-line enforcement). ✅
- **m5** verifier coverage gaps → tiered globs added (see A-F3); g3 branch docstring softened. ✅
- **m6** flip JSONs + amp10 lack per-file loaded-DLL sha/cache-home records → disclosed as deviation in G3_VERDICT limitations + verifier detail strings; harness upgrade (g3_amp_rca meta()) = pending item. ⏳
- **m7** per-column decomposition archived only in derived CSV → disclosed; MINIMAL_REPRO JSON-output archiving = pending item. ⏳
- **m8** FINAL_REPORT "working tree clean" stale → updated at this commit. ✅
- **m9** TEST_PR_DRAFT missing `import math` → added. ✅

Also fixed: A-F4 (external evidence copied in-repo: `release-provenance/raw/miopen_dll_inventory_raw.json`, `official_wheel_urls.txt`, `batchnorm_nostl_vctools_C+D_mission.log` + RELEASE_LINEAGE citations updated) · A-F5 (negative-control JSON got a post-audit annotation explaining the nested `UNEXPECTED_FAIL` classifier label vs authoritative stderr signature; original values untouched) · A-F6 (RELEASE_LINEAGE §4 checklist + pytorch.org channel + 2.13.0-linux note) · B-F7 (negative-control lacks per-run in-process DLL probe — disclosed in G1_VERDICT limitations) · B-F8 (= m3) · B-F9 (perf A/B false "CSVs retained" claim — corrected in PERFORMANCE_REPORT + JSON note) · B-F11 (no-T02 note added to G2_VERDICT) · B-F12 (steady-state spread 6.55–7.09 s + 12.3 s spike at epoch 20 now stated) · C-o3 (fitness key "10" duplicate noted — benign) · C-o4 (cache-state reproduction steps added to checklist row 7) · C-o5 (PR-C matcher never-executed disclosure added).

### Observations recorded (no action)

- A-F7: local `main` branch stale at cb5e8ca (BASELINE_STATE refers to origin/main — live-verified correct); HANDOFF head pointer updated at this commit.
- A-F8: AMD multi-arch index now lists torch-2.13.0+rocm7.14.0 **linux_x86_64** (no Windows wheel) — folded into the weekly-scan checklist (RELEASE_LINEAGE §4).
- C-o1: official-wheel fp16 deltas also vary with cache state (0.264/0.423) — cache sensitivity is NOT ENV-B-only; what is ENV-B-only is crossing the 0.5px threshold. Identical max_rel_diff across envB/envA fresh runs is consistent with quantization-dominated diffs (no fabrication indication).
- C-o2: DLL-embedded build paths (C:/w58m, C:/w58, C:/w56) vs recorded build dirs (C:\b58m, C:\b58) — sha256 is the binding identity; flag for future maintainer questions.
- B-F13: ENV-B amptrack record lacks `trainer_amp_effective` field (FP32-fallback evidence lives in the preserved scrambled log).

## Re-run evidence added this session (new files)

| File | Purpose |
|---|---|
| `raw/g2_detect_envA_amptrack_rerun.{json,loaddll.json,main.log,resume.log}` | Clean ENV-A amptrack re-run: 13/14, t08 FAIL reproduced identically, **0× EvaluateInvokers**, post-hoc probe = official `e97891df` |
| `raw/g1_bn_estimator_probe.json` | Persisted BN estimator probe: 6.812e-08 vs unbiased (45× closer than biased), ENV-B patched context, fresh cache home |
| `raw/scrambled_logs_20261114/` + `raw/README.md` | Preserved superseded logs + forensic name→content mapping |
| `raw/g2_detect_fp32.json` | Canonical ENV-B detect record restored from git `593160e` |
| `release-provenance/raw/miopen_dll_inventory_raw.json`, `official_wheel_urls.txt`, `batchnorm_nostl_vctools_C+D_mission.log` | C4 anchors made in-repo self-contained |

## Net effect on verdicts

- GO-A **CONDITIONAL PASS** — unchanged (env-label corrections only; ENV B = source-built condition unchanged).
- GO-B **CONDITIONAL PASS** — unchanged, with AMP scope honestly narrowed (machinery semantics, not learning) and G4 evidence attributed to the third environment.
- GO-C **NO-GO (BLOCKED_RELEASE)** — unchanged; the "no official package contains the fix" foundation was **strengthened** by live re-verification.
- Upstream submission readiness: drafts corrected before Owner review (issue-draft evidence citations, PR-C scope disclosures, checklist links) — submission still requires Owner approval.

## Deferred / new pending items

1. G4 re-run on ENV A/B with in-process DLL probes (removes the third-environment caveat entirely; harness needs provenance capture added to `g4_long_run.py`/`g4_perf_ab.py`).
2. g3 harness provenance upgrade (per-file DLL sha + cache-home record, m6) + MINIMAL_REPRO JSON-output archiving (m7).
3. CPU simulation of the PR-C matcher against archived tensors before any upstream submission (C-o5).
4. t08 mechanism proof (instrument GradScaler scale trace inside the amptrack lifecycle) — optional.
