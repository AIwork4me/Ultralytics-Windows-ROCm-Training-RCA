# R22A.4.1 Manifest Reconciliation — 261 vs 257 resolved from Git objects

- Generated: 2026-11-17 (mission R22A.4.1 §4, first mandatory P0 audit item)
- Audit subject: the committed Git tree at integration HEAD
  `b1babd8ed4cac447d16db3f8009f4c3c895ba96a` (merge of PR #18; parent PR #17
  merge `4afe2fc6e0f787e36858d43323b67b7d790f4e3f`; original integration HEAD
  `81477298bb25af892a457b57b4401e8c96fb9b15`).
- Method: independent recompute via `git cat-file --batch` blob hashing
  (scratch tooling outside this repository; the repository verifier
  `scripts/verify_release_closure.py` was run separately and agrees).

## 1. Resolution of the 261-vs-257 discrepancy

Both numbers are REAL — they describe different manifest generations. Neither
is wrong for its own generation; the R22A.4 final report's phrasing
"261 entries (228 + 29)" combined the FINAL count with the MERGE-TIME
decomposition, which had become stale by exactly four post-merge entries.

Per-generation counts of `evidence/manifest.json`, recomputed from Git:

| Generation | Ref | Entries | Delta |
|---|---|---|---|
| Integration base | `8147729` | 196 | — |
| PR #17 HEAD | `f903f94` | 225 | +29 (set A, gfx1100 evidence) |
| PR #18 reviewed HEAD (R22A.4 gap-matrix audit point) | `678d3a8` | 212 | +16 (set B, R22A.3 gfx1151) |
| R22A.4 pre-merge commits on PR #18 branch (`5d737be`…`59e90e3`) | — | 241 | +16 (set C, additional warm sample + unified-harness reports) |
| Merge-time union `d2a080a` (= PR #17 ∪ PR #18 branch) | `d2a080a` | **257** | union; A ∩ B = ∅ |
| Post-merge R22A.4 reconciliation commit `50a484f` | `50a484f` | **261** | +4 (set D) |
| Final integration HEAD `b1babd8e` (= PR #18 merge) | `b1babd8e` | **261** | hash-only realignment `e7c93ea`, count unchanged |

Arithmetic identities (all set memberships computed from Git blobs):

- 257 = 228 + 29 where 228 = 196 base + 16 (B) + 16 (C) and 29 = A — this is
  exactly the reconciliation document's sentence, correct AT MERGE TIME.
- 261 = 228 + 29 + **4** where set D is:
  1. `docs/release-closure/R22A4_DUAL_ARCH_SUPPLEMENTAL_RECONCILIATION.md`
  2. `docs/release-closure/R22A4_INITIAL_GAP_MATRIX.md`
  3. `windows-golden-path/reports/r22a4/dual_arch_acceptance.json`
  4. `windows-golden-path/reports/r22a4/gfx1151_supplemental_acceptance.json`
  (added by commit `50a484f`, i.e. AFTER the "257 union" statement was
  computed — the union sentence was not refreshed when the reconciliation
  artifacts themselves entered the manifest.)
- Verdict: **RESOLVED — no duplicate, stale, or phantom entries.** The final
  committed manifest legitimately has 261 unique entries.

## 2. Integrity of the current integrated manifest (261 entries)

Independent `git cat-file --batch` audit at `b1babd8e`:

- 261/261 entry SHA256 match the committed blobs exactly (0 mismatches,
  0 missing blobs).
- 261 unique normalized paths; 0 duplicates; 0 case-insensitive (Windows)
  collisions; 0 absolute/traversal/backslash/self-referential paths;
  0 invalid hash formats.
- Raw-like entries: 240; derived entries: 21.
- Entries introduced per source: PR #17 → 29; PR #18 (R22A.3) → 16;
  R22A.4 pre-merge → 16; R22A.4 post-merge → 4; pre-existing base → 196.
- The two same-path hash "conflicts" between the PR #17 and PR #18 manifests
  (`windows-golden-path/reports/r22a-gfx1151/report.json`,
  `windows-golden-path/reports/r22a-gfx1151/R22A_DUAL_ARCH_MATRIX.json`) are
  both DERIVED files each PR legitimately regenerated from its own side —
  predicted and reconciled by the R22A.4 gap matrix (§M); raw paths have
  zero overlap.

## 3. SHA256SUMS pack manifests (committed, at `b1babd8e`)

Verifier-covered packs (scope of `scripts/verify_release_closure.py`:
`evidence/SHA256SUMS.txt`, `evidence/raw/*/SHA256SUMS.txt`,
`windows-golden-path/reports/*/SHA256SUMS.txt`) — ALL VALID against
committed blobs:

| Pack | Entries | Result |
|---|---|---|
| evidence/SHA256SUMS.txt | 45 | 45/45 blob-exact |
| evidence/raw/p19 | 24 | 24/24 |
| evidence/raw/p19b | 17 | 17/17 |
| evidence/raw/r21 | 18 | 18/18 (2 entries use Windows `\` separators; the verifier's documented normalization resolves them — raw bytes unchanged) |
| evidence/raw/r22-dev | 19 | 19/19 |
| evidence/raw/r22-dev-rerun | 18 | 18/18 |
| evidence/raw/r22a-gfx1151 | 46 | 46/46 |
| evidence/raw/r22a2-gfx1100 | 28 | 28/28 |
| evidence/raw/r22a3-gfx1151 | 29 | 29/29 |
| windows-golden-path/reports/r22a2-gfx1100/SHA256SUMS.txt | 28 | 28/28 |

Repository verifier on this tree: **897 checks, 0 violations**;
adversarial self-tests `scripts/test_verify_release_closure.py`:
**22/22 PASS** (includes path traversal, duplicate-conflicting-hash,
self-referential entry, one-byte content mutation, checksum-matches-only-
uncommitted-file, pack-completeness rejection classes).

## 4. Historical packs OUTSIDE the verifier scope — disclosed, not modified

These predate the R22A git-tree audit and were validated by their
contemporary methods (`sha256sum -c` on the then-working tree). They are
frozen historical records; this mission does NOT rewrite them:

- `evidence/p17/SHA256SUMS_P17.txt`: 17 blob-exact; 92 entries hash the
  CRLF working-tree bytes of files that are committed LF-normalized (same
  latent class R22A.4 repaired for the r22a3 pack) or reference `runs/**`
  artifacts excluded from Git by the repo-wide `runs/` gitignore;
  10 further entries are explicitly declared `(local-only, not committed)`
  in `CHECKPOINT_SHA256SUMS.txt` (disclosed local-only class).
- `evidence/phase3/SHA256SUMS.txt`: 4 blob-exact, 44 mismatch (historical
  generation-hashed disk bytes; `linux_SHA256SUMS.txt` 136/136 is clean).
- `phase5_8/pr13437_round3/SHA256SUMS.txt`: 170 blob-exact, 1 genuine
  mismatch (`raw/yolo/F_r3.log`) — historical Phase-5.8 pack anomaly,
  unrelated to any R22A.4 evidence pack; disclosed for a future phase-5
  cleanup, out of R22A.4.1 scope.
- Extensionless `SHA256SUMS` files under `windows-golden-path/reports/`
  (gp-20261116-093332, r22-dev-candidate, r22-dev-rerun,
  r22-dev-rerun-orchestrated): reference files that were never committed
  (R22-dev-era local-only records); the verifier glob intentionally covers
  only `*.txt` packs.

None of these packs feeds the R22A.4 acceptance verdicts or the 261-entry
authoritative manifest.

## 5. Worktree-only files (this checkout; not evidence of tampering)

- `windows-golden-path/reports/r22a-gfx1151/SHA256SUMS` — UNTRACKED,
  lists 7 `gp*.json` files that were never committed (R22A.1-era local
  generation leftover on the development machine). Classified: worktree-only
  leftover; deliberately NOT committed by this freeze; no committed manifest
  references it.
- `bus.jpg` — untracked test image at repo root; unrelated to evidence.

## 6. Three-form log-hash compatibility (scoping confirmation)

`supplemental_acceptance.load_log_text` accepts the three historical frozen
receipt hash FORMS (exact bytes / LF-normalized / universal-newline decoded
text) ONLY for child-run log authenticity against frozen receipt hashes, and
records `matched_form` per log. It is not used as a general hash fallback:
manifest/blob verification elsewhere is exact-bytes only. Negative tests:
`test_log_sha_verified_both_forms`, `test_log_sha_mismatch_marked`
(tampered content under a matching filename is rejected),
`test_missing_log_recorded`.

## 7. Phase-1 verdict

**RESOLVED — GO.** Manifest arithmetic reconciled from Git objects; all
verifier-required manifests valid at `b1babd8e`; historical out-of-scope
pack anomalies disclosed without modification; no raw evidence touched.
