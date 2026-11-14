# MAINTAINER CHECKLIST — what a maintainer needs to trust each claim

Every row links to a small, runnable artifact. No claim requires trusting the author.

| # | Claim | Smallest proof | Where |
|---|---|---|---|
| 1 | PR #13437 is merged and propagated | `gh pr view 13437 --repo ROCm/rocm-libraries` + compare API ancestor checks | `release-provenance/RELEASE_LINEAGE.md` |
| 2 | No published wheel contains the fix (2026-11-14) | marker scan `miopen_initializer_list`=0 on installed wheel DLL + index scans | `release-provenance/BINARY_PROVENANCE.json`, `WHEEL_MANIFEST.json` |
| 3 | Pre-fix wheel reproduces #3956 exactly | env A + hidden STL probe → 4-part signature | `windows-training-validation/reports/G1_NEGATIVE_CONTROL.json` |
| 4 | Post-fix binary trains without host STL | 16-primitive matrix, 3 isolated cold homes, no-STL env | `windows-training-validation/reports/G1_MATRIX_pm13437_merged_nostl.json` |
| 5 | 7-task lifecycle works end-to-end | `g2_<task>_fp32.json` × 7 (T01-T15 strict semantics) | `windows-training-validation/G2_VERDICT.md` |
| 6 | Resume/checkpoint semantics | interrupt → separate-process resume → 4 epochs | t05/t12 records in each g2 JSON |
| 7 | AMP "anomaly" root cause | `MINIMAL_REPRO.py` (single process, prints per-column diffs) | `amp-rca/ROOT_CAUSE.md` |
| 8 | AMP training genuinely works (official wheel) | 10-epoch probe with per-step scaler anneal | `windows-training-validation/raw/g3_amp10_envA.json` |
| 9 | check_amp fix is minimal & safe | draft diff + reviewer checklist | `upstream-readiness/AMP_FIX_PR_DRAFT.md` |
| 10 | MIOpen EvaluateInvokers anomaly | grep-able error lines in raw logs | `upstream-readiness/MIOPEN_EVALUATEINVOKERS_ISSUE_DRAFT.md` |

## Owner Action Required (external, blocked on humans)

1. **AMD/ROCm release engineering**: cut a release whose rocm-libraries submodule contains f0a5d266 and publish Windows wheels → then re-run G0 checklist (`RELEASE_LINEAGE.md` §4) and the full G1/G2 suites against the official wheel.
2. **Ultralytics maintainers**: review PR-C draft (check_amp) and PR-B/D drafts — submission requires Owner approval per mission boundaries.
3. **MIOpen maintainers**: EvaluateInvokers issue draft.

## Not claimed

- No official-support statement by AMD or Ultralytics is implied anywhere in this repo.
- No cross-architecture claims beyond gfx1151 (see `platform-matrix/GPU_SUPPORT_MATRIX.md`).
- No performance superiority claims (matched A/B limited; see `quality-stability/`).
