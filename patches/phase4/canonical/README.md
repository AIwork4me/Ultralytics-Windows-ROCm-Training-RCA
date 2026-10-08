# Phase-4 canonical patch series — PROVISIONAL, NOT DCO-READY

Generated with `git format-patch` from the canonical two-commit branch
`prepare/miopen-hiprtc-selfcontained` (local worktree
`rocm-libraries-phase4-canonical`, base
`b68f8944300f104875d953fc8e4510908c9aaf0b`):

- `0001-MIOpen-keep-RTC-type-traits-self-contained-when-no-h.patch`
  (commit `c86d1b95aacc35eed6b25e69ba659e1f6a133197`)
- `0002-MIOpen-make-remaining-RTC-kernel-std-includes-self-c.patch`
  (commit `4084759f3804748b7935d882db2d0445a3e0c380`)

Source equivalence to the validated P3-FINAL-R3 series: 8/8 files
byte-identical (Gate P45,
`evidence/phase4/equivalence/file_hash_matrix.json`). A `git am`
round-trip onto a pristine `b68f894` worktree reproduced the identical
8-file content (verified during Gate P46).

## Status: PROVISIONAL LOCAL PACKAGE

- Author/committer: `AIwork4me <AIwork4me@users.noreply.github.com>` —
  the RCA workstream identity. Using it locally does NOT authorize DCO.
- **No `Signed-off-by` is present.** The commit messages carry an
  explicit `DCO: PENDING HUMAN CONFIRMATION` marker line instead.
- Before any upstream submission a human must regenerate these commits
  with the approved real author identity and a legitimate
  `Signed-off-by` trailer, then re-verify equivalence and rerun the
  targeted validation (see `docs/phase4/UPSTREAM_SUBMISSION_CHECKLIST.md`).

Do NOT `git send-email` / `git am` these files into any upstream branch.
