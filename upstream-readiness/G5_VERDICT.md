# G5 VERDICT — Maintainer-Friendly Upstream Readiness

Date: 2026-11-14 · **Verdict: DRAFTS COMPLETE (own repo); upstream submission BLOCKED on Owner approval (mission boundary) + BLOCKED_RELEASE**

## PR package (one purpose each, minimal diffs, runnable proofs)

| PR | Scope | Draft | Runnable proof |
|---|---|---|---|
| **PR-A** | ROCm release tracking / packaging evidence | `release-provenance/RELEASE_LINEAGE.md` + `RELEASE_MATRIX.csv` (traceable ancestry method) | `verify_release_closure.py` + marker probe |
| **PR-B** | Windows ROCm training regression test | `upstream-readiness/TEST_PR_DRAFT.md` (strict-semantics test, SKIP-safe on non-HIP CI) | G1/G2 harnesses already executed on gfx1151 |
| **PR-C** | Minimal AMP precheck fix | `upstream-readiness/AMP_FIX_PR_DRAFT.md` (one function, cross-platform safe) | `amp-rca/MINIMAL_REPRO.py` + raw JSONs |
| **PR-D** | AMD integration docs | `upstream-readiness/DOCS_PR_DRAFT.md` (conditional wording, evidence-dated) | G0 lineage + verdicts |

Plus: **MIOpen issue draft** (`MIOPEN_EVALUATEINVOKERS_ISSUE_DRAFT.md`) for the solver-timing anomaly (new upstream finding, gfx1151, source-built 3.6.2).

## CI strategy (documented, not claimed as executed upstream)

- GitHub-hosted CI: no AMD GPUs → PR-B's test SKIPs by design; logic/compat coverage stays in normal CI.
- Windows AMD self-hosted runner spec: pinned torch/ultralytics versions; GPU-arch gate (refuse to report GPU PASS without `torch.version.hip` + device match); JUnit XML + provenance JSON + logs artifacts; timeouts; labels isolating GPU jobs.
- Security: self-hosted GPU runners must not execute untrusted PR code (credential-host risk) — evaluate `pull_request_target` exposure; recommended: maintainers-only label gating. Documented in TEST_PR_DRAFT/G5 — not claimed as running anywhere.

## Docs readiness

`DOCS_PR_DRAFT.md` separates native-PyTorch-ROCm-training from ONNX Runtime MIGraphX; all support wording is conditional on verified scope (gfx1151, listed wheels, FP32 + verified AMP) with dated evidence links. No official-support language (enforced by `verify_release_closure.py` pattern scan).

## G5 PASS conditions

- Maintainer-friendly tests prepared: **DONE** (draft + executed superset locally)
- CI strategy: **DONE** (documented; execution requires runner infra — Owner Action Required)
- Documentation: **DONE** (draft)
- Actual upstream PRs: **NOT CREATED** — mission §2.4 forbids upstream submission without explicit Owner approval; drafts wait in this repo.
