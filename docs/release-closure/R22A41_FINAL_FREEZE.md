# R22A.4.1 Final DEV Freeze — Windows Radeon dual-architecture training baseline

- Generated: 2026-11-17 (mission R22A.4.1, Phases 8–9)
- Nature: COMMIT-STABLE freeze record. A file committed inside a Git commit
  cannot contain that commit's own final SHA; the exact final integration
  SHA and its independently attributable CI run are attested EXTERNALLY in
  the R22A.4.1 PR description (updated post-merge without new commits) and
  in the mission report. This document freezes the CONTRACT and the
  VERIFICATION METHOD, both of which are commit-stable.

## A. Identity

- Repository: `AIwork4me/Ultralytics-Windows-ROCm-Training-RCA`
- Integration branch: `work/windows-rocm-training-release-closure`
- Freeze-parent integration HEAD (audited baseline): `b1babd8ed4cac447d16db3f8009f4c3c895ba96a`
  - = merge of PR #18 (parents: PR #17 merge `4afe2fc6e0f787e36858d43323b67b7d790f4e3f`
    + PR #18 HEAD `e7c93ea5c6b7452cbeb8ca15527d597b49898e08`)
  - PR #17 lineage: original integration HEAD `8147729` + PR #17 HEAD `f903f94`
- R22A.4.1 change branch: `audit/r22a4-1-final-integration-freeze` → PR
  targeting the integration branch (NOT `main`; `main` untouched at `f9f745e`).
- Final integration HEAD: produced by merging the R22A.4.1 PR; its exact SHA
  + CI attestation live in the PR description (external record, see §D).

## B. Evidence

- gfx1100 evidence pack: `evidence/raw/r22a2-gfx1100/` (46+28 files, byte-frozen,
  SHA-verified in `evidence/manifest.json` and pack `SHA256SUMS.txt`)
- gfx1151 evidence pack: `evidence/raw/r22a3-gfx1151/` (frozen five + recovered
  child logs + additional sample `R22A4-B-ADD1`), byte-frozen, SHA-verified
- DEV package lock: `evidence/raw/r22a-gfx1151/R22A_GFX1151_PACKAGE_LOCK.json`
  (blob SHA256 `97a2da63…8533` = the additional sample's `wheel_lock_sha256`)
- Manifest inventory at the freeze-parent: 261 entries, 261/261 blob-exact
  (generations: 196 base + 29 PR#17 + 16 PR#18/R22A.3 + 16 R22A.4 pre-merge
  + 4 R22A.4 post-merge). Freeze HEAD adds only the R22A.4.1 DERIVED
  artifacts listed in `R22A41_FINAL_CONSISTENCY_MATRIX.md`; the verifier
  enforces every entry against committed blobs.
- Historical hash-form compatibility: the three log-hash FORMS (exact bytes /
  LF-normalized / universal-newline text) remain narrowly scoped to child-log
  authenticity; manifest/blob verification is exact-bytes only.
- Evidence integrity verdict: **PASS** (897 checks / 0 violations at the
  freeze-parent; freeze HEAD re-verified with the added entries).

## C. Acceptance

- gfx1100 physical training: PHYSICAL_TRAINING_FUNCTIONAL_PASS;
  strict evidence: RELEASE_GRADE_EVIDENCE_ACCEPTED (per-arch
  R22A2_GFX1100_SUPPLEMENTAL_PASS) — recomputed.
- gfx1151 physical training: PHYSICAL_TRAINING_FUNCTIONAL_PASS;
  strict evidence: RELEASE_GRADE_EVIDENCE_ACCEPTED (per-arch
  R22A3_GFX1151_SUPPLEMENTAL_PASS) — recomputed.
- Combined verdict: **R22_DEV_DUAL_ARCH_SUPPLEMENTAL_VALIDATED** (ceiling
  DEV_CANDIDATE) — recomputed by ONE unified engine
  (`windows-golden-path/scripts/supplemental_acceptance.py --dual`),
  adapters `r22a2-flat-v1` / `r22a3-nested-v1`.
- Additional-sample runtime provenance (R22A4-B-ADD1):
  RECEIPT_RUNTIME_CLASS=INCONCLUSIVE (verbatim) /
  AUTHORITATIVE_PACKAGE_PROVENANCE=DEV_LOCK_VERIFIED /
  RUNTIME_IDENTITY_MATCH=MATCH / ACCEPTANCE_DISPOSITION=PROVENANCE_ACCEPTED_DEV.
- Machine-readable record (deterministic, embeds input git-blob SHA256s and
  harness-code SHA256s): `windows-golden-path/reports/r22a41/r22a41_dual_arch_acceptance.json`.

## D. Verification (method + freeze-parent results)

- CPU contract tests: 197 passed / 0 failed / 0 skipped at the freeze HEAD
  (183 R22A.4 baseline preserved + 11 provenance-gate + 3 wrapper-compat).
- Adversarial verifier self-tests: 22/22 PASS.
- Git-tree evidence verifier: 0 violations (897 checks at freeze-parent;
  re-run green at freeze HEAD with the added manifest entries).
- Compile: `python -m compileall -q windows-golden-path` clean.
- Determinism: the r22a41 dual report regenerates byte-identically.
- Exact-HEAD CI (the third P0 item): the merged integration HEAD receives
  its OWN `cpu-contract` run via `workflow_dispatch` (push events do not
  trigger this workflow); PR-HEAD CI alone is NOT claimed as integration CI.
  Run URL/ID/head-SHA/conclusion are attested in the PR description.
- CI workflow under test: `.github/workflows/cpu-contract.yml`
  (compileall + pytest + verifier + adversarial, windows-latest, Python 3.11).

## E. Limitations — DEV supplemental success does NOT prove

- AMD Official Stable wheel readiness (still BLOCKED_RELEASE: newest official
  Windows wheel torch 2.12.0+rocm7.14.1 lacks the PR #13437 fix).
- Official Stable dual-architecture validation.
- Clean Windows installation (G9 not run).
- Independent end-user reproducibility.
- R23 production release readiness.
No dGPU-vs-APU performance comparison is made or implied.

## F. Freeze restrictions

- Frozen: every path under `evidence/raw/**` (byte-exact), the frozen
  receipts' verdict fields (incl. `runtime_class` values), the acceptance
  contract semantics in `supplemental_acceptance.py` (Part A/B recompute,
  cache-role derivation from home identity, monitor fail-closed, stored-PASS
  rejection, runtime-provenance gate), and the CPU adversarial test
  semantics.
- Any future material change requires a NEW commit identity, NEW
  verification, and an updated acceptance record — the historical freeze is
  never mutated in place.
- Historical out-of-scope pack anomalies (p17/phase3/phase5_8 disk-byte
  manifests, extensionless local-only report manifests) are DISCLOSED in
  `R22A41_MANIFEST_RECONCILIATION.md` §4 and intentionally left untouched.
