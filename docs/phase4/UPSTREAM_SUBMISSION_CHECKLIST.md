# Upstream Submission Checklist (Gate P57 deliverable)

Human steps remaining before any ROCm/rocm-libraries submission. Phase 4
stopped before submission by design.

## 1. DCO / identity (BLOCKING)

- [ ] Approve the real author name + email for the upstream contribution.
- [ ] Recreate the two commits with that identity (same tree bytes; only
      author/committer metadata changes) and a legitimate
      `Signed-off-by:` trailer replacing the
      `DCO: PENDING HUMAN CONFIRMATION` marker line.
- [ ] Regenerate `patches/phase4/canonical/*.patch` via `git format-patch`
      from the final commits.
- [ ] Re-verify the 8/8 byte-equivalence (rerun
      `scripts/phase4/semantic_equivalence.py` against the new commits).

## 2. Copyright (BLOCKING)

- [ ] Fill `[contributor name and notice to be set by the submitter]` in
      the MIT headers of the three new freestanding files (maintainer
      preference from Phase-3 review).
- [ ] This changes the validated bytes → rerun the targeted validation:
      CI matrix (P49) + build + P51/P52-style runtime spot-check on the
      new candidate series.

## 3. Formatting / cleanups (submitter decision; each changes validated
##    bytes → new candidate → rerun validation as in #2)

- [ ] Decide whether to run clang-format on the 8 files (currently NOT
      format-clean; 2 of 4 modified files were not clean at baseline
      either). See `docs/phase4/AUTHORSHIP_DCO_AUDIT.md`.
- [ ] Reviewer A (P56) cleanups, all optional polish:
      reword commit 2's message ("runtime path" phrasing — the
      builtin-limits change in radix.hpp is unconditional, not
      RTC-scoped; message-only change, tree bytes unaffected); drop or
      use the currently-dead `MIOPEN_FREESTANDING_TRAITS_ACTIVE` macro;
      fix the triple blank line in
      `miopen_freestanding_initializer_list.hpp`; do NOT remove the
      offline `#include <limits>` from radix.hpp (transitive users).

## 4. PR text

- [ ] Refresh `docs/phase4/PR_DRAFT_FINAL.md` with the final commit
      hashes and any maintainer-requested changes.
- [ ] Associate with issue #3956; mention #7718, TheRock#8292 context.

## 5. Pre-submission verification

- [ ] Re-check applicability on current develop that day
      (`git apply --check` ordered series in a clean worktree;
      Gate P42 method).
- [ ] Confirm no equivalent fix landed meanwhile
      (`git grep -l __has_include origin/develop -- projects/miopen/src/kernels/`
      empty + freestanding files absent).

## 6. Forbidden until explicit human approval

- Any `gh pr create` / `gh issue create` / comment against ROCm repos;
  any push to ROCm/rocm-libraries; any claim of upstream acceptance.

Phase-4 status fields that must remain false unless a human flips them:
`upstream_pr_created`, `upstream_issue_created`, `upstream_comment_posted`,
`internal_pr_created`.
