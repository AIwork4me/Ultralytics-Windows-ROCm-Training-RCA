# R22A.4.1 Final Consistency Matrix

- Generated: 2026-11-17 (mission R22A.4.1 §8)
- Baseline audited: integration HEAD `b1babd8ed4cac447d16db3f8009f4c3c895ba96a`
  + the R22A.4.1 freeze changes on `audit/r22a4-1-final-integration-freeze`.
- Historical claims are quoted from the R22A.4 committed documents and the
  R22A.4 user-facing final report; raw receipts were never edited.

| Item | Historical claim | Actual verified value | Source of truth | Action |
|---|---|---|---|---|
| Manifest union | "261 entries (228 + 29)" vs reconciliation "257 (228 + 29)" | **Both real, different generations**: merge-time union 257 = 228 + 29; final 261 = 228 + 29 + **4** post-merge R22A.4 artifacts (2 docs + 2 report JSONs, commit `50a484f`). 261/261 hashes match committed blobs; 0 dups/hygiene violations | Git objects (`git cat-file --batch`) | Reconciled — [`R22A41_MANIFEST_RECONCILIATION.md`](R22A41_MANIFEST_RECONCILIATION.md) |
| Manifest generations | base 196 → PR#17 225 / PR#18 212 | recomputed identical; PR#17 +29, PR#18(R22A.3) +16, R22A.4 pre-merge +16, post-merge +4 | Git objects | Verified |
| CPU tests | 183 passed | **183 preserved + 14 added = 197 passed**, 0 failed, 0 skipped; every unique negative behavior retained (spoof/cache/monitor/adversarial classes unchanged) | `python -m pytest windows-golden-path/tests -q` | Verified (coverage superset) |
| Verifier checks | 897 checks, 0 violations (R22A.4 final state) | 897 / 0 at `b1babd8e`; freeze HEAD adds checks for the new manifest entries (exact count recorded in the freeze evidence) | `scripts/verify_release_closure.py` | Verified |
| Adversarial self-tests | 22/22 | **22/22 PASS** (traversal, dup-conflict, self-ref, one-byte corruption, uncommitted-checksum, pack-completeness, …) | `scripts/test_verify_release_closure.py` | Verified |
| Dual-arch verdict | R22_DEV_DUAL_ARCH_SUPPLEMENTAL_VALIDATED | recomputed identical via ONE unified engine incl. the new provenance gate; every fact cell matches (gfx1100 11/6/5, gfx1151 11/7/4, 366/366, 48/48, workers 8, 13 ids, roles [cold,cold,cache_priming,warm,warm,warm]) | `reports/r22a41/r22a41_dual_arch_acceptance.json` (deterministic; input blob hashes embedded) | Verified |
| Runtime provenance (additional sample) | receipt INCONCLUSIVE; "classification authority remains the package-lock provenance gate" (narrative only) | now MECHANICALLY enforced: `runtime_provenance_gate` four-field classification, wired into `--dual` (fail-closed); disposition PROVENANCE_ACCEPTED_DEV | committed lock blob hash + frozen receipts + 11 tests | Verified + hardened |
| r22a3_acceptance wrapper | docstring example `--part-b R22A3_WORKERS8_RUNS.json` | **crashed** (`part_b.get` on list) at `b1babd8e` — latent compat defect; fixed (accepts list or dict); 3 regression tests incl. AST proof the stored-PASS read never returns | pytest `TestR22A3AcceptanceCompat` | Fixed |
| Wrapper verdict semantics | "wrapper reports NO-GO for the original receipt alone" | actually `PARTIAL_PASS` (PartA PASS + PartB honest NO_GO: "expected exactly 3 qualifying pre-warmed runs, found 2"); docstring wording "NO-GO for the original receipt alone" refers to the PartB gate, exit code is 1 either way | wrapper output on real pack | Clarified (behavior unchanged, documented) |
| Historical CI claims | PR #17 run 43862231878 / PR #18 run 43896566659 PASS | correctly cited as PR-HEAD-historical in committed docs; no committed doc claims integration-HEAD CI | gap matrix + `gh api` | Verified (no stale claim) |
| Verifier count statement | "825+ checks, 0 violations" (R22A.4 reconciliation, merged tree) | historical statement, still true (897 ≥ 825); actual values recorded above | verifier | No change (historical) |
| Final CI (this freeze) | — | PR-HEAD `cpu-contract` run on the R22A.4.1 PR + **post-merge `workflow_dispatch` cpu-contract on the exact integration HEAD**; run IDs/URLs/head-SHA/checkout attested EXTERNALLY in the PR description and the mission report (commit-stable docs reference the mechanism, not mutable run IDs) | GitHub Actions API | Executed in Phase 7 (see PR) |
| Manifest at freeze HEAD | 261 | + R22A.4.1 entries (r22a41 report, audit docs, freeze docs); exact count at the freeze HEAD recorded in `R22A41_FINAL_FREEZE.md` and enforced by the verifier | Git tree + verifier | Updated (derived, deterministic) |
| Verdict ceiling | DEV_CANDIDATE max | unchanged; OFFICIAL_STABLE / R23_RELEASE_READY / CLEAN_WINDOWS_INSTALL NOT claimed anywhere | all reports | Enforced |

## New R22A.4.1 artifacts (all DERIVED; raw evidence untouched)

- `docs/release-closure/R22A41_MANIFEST_RECONCILIATION.md`
- `docs/release-closure/R22A41_RUNTIME_PROVENANCE_AUDIT.md`
- `docs/release-closure/R22A41_FINAL_CONSISTENCY_MATRIX.md` (this file)
- `docs/release-closure/R22A41_FINAL_FREEZE.md` (commit-stable freeze record)
- `windows-golden-path/reports/r22a41/r22a41_dual_arch_acceptance.json`
  (deterministic; embeds input-evidence git-blob SHA256s + harness-code SHA256s)

## Code changes (minimal, fail-closed direction only)

- `windows-golden-path/scripts/supplemental_acceptance.py`:
  `runtime_provenance_gate()` + `_therock_revision()`; dual report gains
  `additional_sample_provenance` (enforced: non-accepted gate ⇒ NO-GO),
  `input_evidence`, `harness_code_sha256`, `schema_adapters`.
- `windows-golden-path/scripts/r22a3_acceptance.py`: part-B list|dict compat
  fix (the documented CLI example no longer crashes).
- `windows-golden-path/tests/test_harness_cpu.py`: +14 tests
  (`TestRuntimeProvenanceGate` 11, `TestR22A3AcceptanceCompat` 3).

No verifier weakening, no G8 workers=0 change, no new mandatory CI dependency
(psutil still optional), no remote downloads, no raw-evidence path touched.
