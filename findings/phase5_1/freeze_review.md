# Independent Freeze-Integrity Review — P5.1-CANDIDATE-R1

- **Verifier:** independent subagent (did NOT produce any of the artifacts; did NOT
  read `scripts/phase5_1/` — verification code written from scratch, Python stdlib only)
- **Date:** 2026-10-08
- **Machine-readable results:** `evidence/phase5_1/freeze_integrity.json`
  (schema `phase5_1_freeze_integrity_v1`, 14 check records)
- **Inputs of record:** `findings/phase5_1/FINAL_HANDOFF.json` (manifest),
  Git objects of the shared store / candidate worktree, raw bytes under
  `patches/phase5_1/canonical/`, evidence JSON bytes under `evidence/phase5_1/`,
  both handoff docs.

## Method

Every check was recomputed from primary sources with the verifier's own code:

1. Manifest identity fields read and compared literally.
2. Commits resolved via `git cat-file`/`git log` against the candidate worktree
   (`rocm-libraries-phase5.1-candidate`, linked worktree of the shared store);
   parent chain and HEAD compared to the manifest; subjects compared to
   `git log --reverse --format=%s base..HEAD`.
3. Patch SHA256/byte-lengths recomputed from the file bytes on disk
   (sorted 0001/0002/0003); CR-byte count checked (CRLF-corruption probe).
4. Series SHA256 recomputed as SHA256 over the three files' bytes concatenated
   in order, no separator (`sha256_file_concat_v1`).
5. Source reconstruction from the frozen base `7c5866144ac4b879be442563e2b49fa1c142ea36`
   in FRESH temporary worktrees, three independent ways:
   - **git am** (primary, task-sanctioned): worktree add --detach at base,
     `git am` 0001→0002→0003, compare `HEAD^{tree}`;
   - **git apply** (consumer path): every base-side file the patches touch written
     byte-exact from the BASE blobs (the shared clone is sparse-cone, see NIT-1),
     then plain `git apply` x3, `git add --sparse -A`, `git write-tree`;
   - **index-only**: `read-tree base^{tree}` + `git apply --cached` x3 +
     `git write-tree --missing-ok` (no working tree at all).
   All temp worktrees removed (`git worktree remove --force` + physical retry;
   verified gone from `git worktree list` and the temp dir).
6. Copyright/DCO checked against the actual HEAD blobs (`git cat-file blob HEAD:<path>`)
   and full commit bodies (`git log --format=%B`), plus working-tree==blob byte equality.
7. Evidence cross-checks: `build_provenance.json`, `ci_matrix_phase5_1.json`,
   `runtime_validation.json`, `yolo_train.json` parsed and compared to the manifest
   (including DLL-SHA256 consistency across all four files and honesty of the
   `amp_genuine=false` record).
8. Stale-ID scan: 64-hex strings masked first, then every 7–40 hex run in
   `docs/phase5_1/LINUX_FINAL_VALIDATION_HANDOFF.md` matched against the
   allowlist (base, 3 candidate commits incl. prefixes, P3/P4 historical,
   superseded P5 series); same scan run on the old phase5 doc for the
   supersession check.

## Per-check results

| ID | Check | Result |
|----|-------|--------|
| CHK-01 | Manifest schema_version=1, handoff_type, candidate_id | PASS |
| CHK-02 | Commit existence, parent-chain order (c0←base, c1←c0, c2←c1), HEAD==c2 | PASS |
| CHK-03 | Patch SHA256 + byte sizes recomputed from disk (0001/0002/0003; 0 CR bytes each) | PASS |
| CHK-04 | Series SHA256 `sha256_file_concat_v1` recomputed | PASS |
| CHK-05 | Reconstruction tree == candidate `HEAD^{tree}` == manifest tree (3 methods) | PASS |
| CHK-06 | Commit subjects == `git log --reverse --format=%s base..HEAD` | PASS |
| CHK-07 | Copyright line / placeholder absence / MIT text in 4 HEAD blobs | PASS |
| CHK-08 | No `Signed-off-by:`; `DCO: PENDING HUMAN CONFIRMATION` on all 3 commits; manifest PENDING | PASS |
| CHK-09 | windows_validation evidence matches final source state (head, DLL sha, CI/runtime/yolo PASS, amp_false_pass=true) | PASS |
| CHK-10 | `linux_validation_status` == exactly "PENDING" | PASS |
| CHK-11 | All upstream-action flags false; only origin ROCm URL; no pushed candidate branch | PASS |
| CHK-12 | Stale-hex scan of docs/phase5_1 handoff (after masking sha256s) | PASS |
| CHK-13 | Old phase5 doc superseded correctly; no stale hex in instruction context | PASS |
| EX-01 | Manifest `changed_files_vs_base`: 10/10 git_blob/sha256/bytes == actual HEAD blobs | PASS |

### Key recomputed identities

- Series SHA256 (recomputed): `797a69b5ae86d0e304b2258b5f5323cc97241a413d2c43134bf01703f7842f6d`
  (matches manifest `series_hash.sha256`)
- Reconstructed source tree (git am, git apply, and index-only — all three agree):
  `605d0d214acdbc06086fdb27c61fec970c0f2798` == candidate `HEAD^{tree}` ==
  manifest `source_tree_identity.head_tree_sha1`
- Commit chain (single-parent, ordered):
  `d4003de1a7ca…` ← base `7c5866144ac4…`;
  `3b18a0655b99…` ← `d4003de1…`;
  `e7ff6d75fac3…` ← `3b18a065…`; worktree HEAD == `e7ff6d75fac3e7b683e81e671555ada99af13b74`
- Patch bytes: 15546 / 7444 / 27631 bytes, **zero CR bytes** (no CRLF corruption);
  individual SHA256s match the manifest exactly.
- Windows evidence: `build_provenance.source_git_head` == HEAD commit;
  DLL SHA256 `9a7744029ccdf421f8ee2df588b02e35e9b5c829a7079f6dc18411cd0adb11e7`
  identical in build/runtime (2 places)/yolo (2 places) evidence and the manifest;
  CI 13/13 cells overall PASS; runtime overall PASS; `amp_false_pass=true`.
  Evidence timestamps strictly precede manifest generation (15:24→15:34 < 15:44).
- Upstream safety: `git remote -v` shows only `origin → https://github.com/ROCm/rocm-libraries.git`;
  remote branches = `origin/develop` only; no remote branch contains HEAD.

## Verdict tokens

| Token | Value |
|-------|-------|
| PATCH_IDENTITY_MATCH | true |
| COMMIT_CHAIN_MATCH | true |
| SERIES_SHA256_MATCH | true |
| SOURCE_TREE_MATCH | true |
| NO_STALE_HANDOFF_IDS | true |
| LINUX_PENDING_RECORDED | true |

## Findings

**BLOCKER:** none.

**MAJOR:** none.

**MINOR:** none.

**NIT (documentation/disclosure only, none affect the freeze):**

1. **NIT-1 — environment note (verification-side, not a candidate defect).** The
   shared main clone is a partial (`blob:none`) + sparse-cone repo
   (`core.sparseCheckout=true`, cone ≈ `projects/miopen/src/kernels`), so a fresh
   linked worktree does not materialize `projects/miopen/test/`. A first
   plain-`git-apply` attempt failed with
   `projects/miopen/test/CMakeLists.txt: No such file or directory` purely because
   that base file was absent from disk. After writing the exact BASE blob bytes for
   every patch-touched file (hash-verified), plain `git apply` 0001→0002→0003
   applied cleanly and reproduced the exact tree — i.e. the handoff doc's
   consumer instruction (`git checkout <base> && git apply 0001..0003`) is valid on
   a normal full clone. Recorded for reproducibility.
2. **NIT-2 — copyright line decoration.** In all four files the attribution line
   is ` * Copyright (c) 2026 AIwork4me` (line 5, standard C block-comment
   decoration ` * `). Stripping comment decoration, each file contains exactly one
   copyright line, its text exactly `Copyright (c) 2026 AIwork4me`, no other
   copyright holder lines, no `[contributor name and notice to be set by the
   submitter]` placeholder, and the MIT grant sentence
   ("Permission is hereby granted, free of charge") verbatim. A literal
   undecorated line cannot exist inside a C/C++ block comment, so the decorated
   form is judged to satisfy the requirement.
3. **NIT-3 — allowlist-vs-scan.** The stale-ID scan flags the head TREE SHA
   `605d0d214acdbc06086fdb27c61fec970c0f2798` (40-hex, appears 3x in the phase5_1
   handoff) because the allowlist contains only commit IDs. It is NOT stale: it is
   the current authoritative tree identity, independently reproduced four ways
   (candidate `HEAD^{tree}`, git am, git apply, index-only). No other non-allowlisted
   hex token exists in either doc after masking 64-hex SHA256 strings.
4. **NIT-4 — old phase5 doc retains superseded instructions.**
   `docs/phase5/LINUX_FINAL_VALIDATION_HANDOFF.md` opens with a prominent
   SUPERSEDED banner pointing to `findings/phase5_1/FINAL_HANDOFF.json` +
   `docs/phase5_1/LINUX_FINAL_VALIDATION_HANDOFF.md` (P5.1-CANDIDATE-R1) and
   explicitly says not to validate the P5 series below unless re-aimed. The
   correction note describes the removed obsolete intermediate IDs without any hex.
   The only hex token in its instruction section is the base SHA abbreviation
   `7c58661` (allowed; identical base for P5.1). Residual risk: a reader who skips
   the banner could follow superseded instructions — mitigated by the banner, and
   out of scope for a freeze-integrity blocker.

**Honesty spot-checks (adversarial):** manifest's `yolo_amp_note` claims
`amp_genuine` on P5.1 = FALSE — `yolo_train.json` records `amp_genuine:false` for
both amp_false and amp_default runs, consistent (no exaggeration found). The
manifest's "13/13 cells" CI claim matches the 13 cells present in
`ci_matrix_phase5_1.json` with `overall: PASS`. DCO status string
(`DCO_ATTESTATION_PENDING…`) matches the actual absence of `Signed-off-by:`
trailers and presence of `DCO: PENDING HUMAN CONFIRMATION` marker lines on all
three commits.

FREEZE VERDICT: PASS
