# Gate Reviews B02 + B03 — Independent Subagent Audits (W7900-PHASE52-BRIDGE-R1)

Auditor: fresh-context general subagent, read-only over frozen evidence,
instructed to attack the consumer independently.

## B02 — Schema contract and input-validation audit

VERDICT: **PASS**

Confirmed the corrected consumer validates the ACTUAL frozen schema
(base_sha, ordered_commits, ordered_patches[{order,path,sha256,bytes}],
series_hash.algorithm=='sha256_file_concat_v1', series_hash.sha256,
source_tree_identity.head_tree_sha1, linux_validation_status=='PENDING',
authorization_to_submit_upstream==false, DCO/copyright interpretation) and
rejects provisional keys (upstream_base_sha / patch_series /
series_sha256_mode / rca_evidence_commit) with no fallback.

Pinned RCA checkout enforcement confirmed: HEAD == --rca-evidence-sha,
clean status, every declared patch byte-compared to git blob HEAD:<path>.

## B03 — Attempted bypass attacks (auditor's own, beyond the 22-case matrix)

| Attack | Observed | Intended reason confirmed |
|---|---|---|
| own throwaway git copy (control) | PASS | yes (control) |
| swap entry[0].path to another patch file | FAIL | yes (sha/size/dup/unexpected-file) |
| manifest tampered, uncommitted | FAIL | yes (DIRTY checkout) |
| non-git rca-root | FAIL | yes (not a git checkout) |
| symlinked parent dir component | FAIL | yes (symlink component) |
| manifest outside root + forged informational fields | PASS | gap -> F1 |
| series algorithm 'hash_chain' | FAIL | yes |
| linux_validation_status 'PASS' | FAIL | yes |
| authorization_to_submit_upstream true | FAIL | yes |
| 2-patch series | FAIL | yes (contiguity/unexpected-file/series) |
| 22-case harness re-run | ALL_ATTACKS_OK=True | yes x22 |

## Findings and resolutions

- F1 (MINOR) manifest sha256 not pinned / informational fields forgeable:
  FIXED — EXPECTED.manifest_sha256 pin added (--expect-manifest-sha256
  override documented for adversarial tests), and when the manifest is read
  from inside the pinned checkout it is now byte-matched against its git
  blob (blob_matches_worktree). Security-relevant fields were already
  pinned; now the whole frozen manifest is.
- F2 (MINOR) harness not re-runnable (makedirs exist_ok crash): FIXED —
  verified two consecutive clean runs.
- F3 (MINOR) exit codes null in matrix for A-U: FIXED —
  run_check stashes consumer_exit_code; matrix records exit codes for all
  attacks (verified all non-null).
- F4 (NIT) frozen_evidence_untouched asserted not verified: FIXED — harness
  now runs git status + rev-parse on the pinned repo and records the real
  boolean (verified true).
- F5 (NIT) effective expect-* pins invisible in PASS evidence: FIXED —
  check-only report now embeds effective_expect_pins.
- F6 (NIT) symlinked .git accepted by isdir: FIXED — explicit islink
  rejection added; double cat-file spawn collapsed to one.

Post-fix re-verification (primary agent): harness run 1 + run 2 ->
ALL_ATTACKS_OK=True, frozen_untouched=True (real check), all exit codes
recorded; valid manifest -> PASS exit 0 with pins recorded.
