# Authorship, DCO, Copyright and Formatting Audit (Gate P54)

Date: 2026-10-08. Audited object: canonical two-commit branch
`prepare/miopen-hiprtc-selfcontained` (`c86d1b9`, `4084759` on
`b68f8944300f104875d953fc8e4510908c9aaf0b`) and its `git format-patch`
output archived at `patches/phase4/canonical/`.

## Classification

```text
PROVISIONAL LOCAL PACKAGE   (current state)
DCO-APPROVED SUBMISSION PACKAGE (NOT achieved; requires human action)
```

## Git identity

- Author = Committer = `AIwork4me <AIwork4me@users.noreply.github.com>` on
  both commits — the configured identity of the RCA workstream, used for
  local reconstruction only. It has NOT been approved as the DCO identity
  for the upstream contribution.
- Dates: `2026-10-08 10:49:05 +0800` (real, same clock, scripted cadence —
  P44 reviewer NIT, within spec).

## Signed-off-by / DCO

- Neither commit contains a `Signed-off-by` trailer. `git log --format=%B`
  scan (P44 reviewer): zero valid sign-off lines.
- The validated patch envelopes' placeholder
  (`Signed-off-by: <AUTHOR NAME> <author@example.com>  # DCO: fill in
  before submission`) was NOT copied into the commits; each commit message
  carries an explicit `DCO: PENDING HUMAN CONFIRMATION - provisional local
  commit, not for upstream submission; ...` marker line instead.
- The archived format-patch files each contain exactly one DCO-pending
  marker and no placeholder author strings (grep-verified).

```text
DCO_PENDING_HUMAN_CONFIRMATION
```

## Placeholder sweep (canonical tree + phase-4 patches)

- `<AUTHOR NAME>` / `author@example.com`: none in the canonical patches;
  none introduced by the two commits (the placeholders exist only in the
  immutable Phase-3 patch envelopes, by design).
- `# DCO: fill in before submission`: none in canonical commits/patches.
- `[contributor name and notice to be set by the submitter]`: present
  exactly in the MIT headers of the three new files
  (`miopen_freestanding_{type_traits,utility,initializer_list}.hpp`) —
  intentional, flagged as a human submission step (maintainer-preference
  attribution, per Phase-3 final readiness).

## Commit / patch format

- `git diff --check b68f894..HEAD`: clean (no whitespace errors).
- New-file sections well-formed (`new file mode 100644`, `--- /dev/null`).
- format-patch headers: real commit hashes/dates, subject wrapped at 72
  cols, `git am` round-trip reproduces the identical 8-file content
  (P46). Signature line carries the authentic local git version
  (2.55.0.windows.5) — the validated Phase-3 envelopes' placeholder
  `2.x.y` signature is not carried over.
- No binaries in the commits (numstat all-numeric).

## Clang-format (measured with clang-format 23.1.3, `--style=file`)

| File | Baseline (b68f894) | Canonical (patched) |
|---|---|---|
| `miopen_type_traits.hpp` | conforms | VIOLATES (new `#error` line > limit) |
| `miopen_utility.hpp` | VIOLATES (4 pre-existing) | VIOLATES |
| `radix.hpp` | VIOLATES (4 pre-existing) | VIOLATES |
| `tensor_view.hpp` | conforms | VIOLATES |
| `miopen_freestanding_type_traits.hpp` | n/a (new) | VIOLATES |
| `miopen_freestanding_utility.hpp` | n/a (new) | VIOLATES |
| `miopen_freestanding_initializer_list.hpp` | n/a (new) | VIOLATES |

Decision: **no reformatting applied in Phase 4.** Reformatting would change
the eight validated source files, breaking the 8/8 byte-equivalence hard
gate (P45) and reclassifying the series as a new candidate requiring full
revalidation (mission quality principle). Two of the four modified files
already violate the repo `.clang-format` at the validated baseline, so the
repo's kernels are not format-clean in general. Recorded as a
**submission-time human decision** (MINOR): if upstream reviewers request a
clang-format pass, it must be done as a follow-up candidate with re-run
targeted validation.

## Required human actions before submission

1. Approve the real author identity + `Signed-off-by` (DCO).
2. Replace the `DCO: PENDING HUMAN CONFIRMATION` marker line in both
   commit messages with the legitimate sign-off; regenerate format-patch.
3. Fill the MIT copyright attribution in the three new-file headers.
4. Decide on the clang-format question (see above).
5. Re-verify byte-equivalence and rerun the targeted validation after any
   of the above that touches the validated files (only #3/#4 do; #1/#2 are
   metadata-only and leave tree bytes unchanged).
