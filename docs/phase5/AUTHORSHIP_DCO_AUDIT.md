# Authorship, Email and DCO Audit (Gate P5-15)

Date: 2026-10-08. Final Phase-5 series (post-panel amendment): `135f775e` / `66f66944` / `29846fc4`
on branch `prepare/miopen-hiprtc-phase5` (worktree
`rocm-libraries-phase5-candidate`).

## 1. Git identity (VERIFIED)

All three commits:

```text
Author:     AIwork4me <AIwork4me@users.noreply.github.com>
Committer:  AIwork4me <AIwork4me@users.noreply.github.com>
git log -3 --format=fuller  — consistent; git diff --check — clean;
git show --stat per commit — scope matches the commit subjects.
```

The user explicitly confirmed (Phase-5 mission header): the real Git
author name is `AIwork4me`, and the user personally owns and controls
that GitHub identity. Authorship identity: **established**.

## 2. Email ownership (VERIFIED — not inferred from string similarity)

GitHub links BOTH of the account's addresses to login `AIwork4me`
(account id `261514469`, created 2026-02-13), verified read-only via the
REST API on this repository's commits:

| Email | Evidence (commit) | API `author.login` |
|---|---|---|
| `AIwork4me@users.noreply.github.com` | pushed commit `7294c66` (phase-4 tip, authored with this email) | `AIwork4me` (linked) |
| `AIwork4me@qq.com` | merge commit `033e6f4` created via GitHub web UI while signed in as the account | `AIwork4me` (linked) |

GitHub only links a commit to an account when the email is verified on
that account (pushed) or the commit was made by the signed-in account
(web UI). Both paths are demonstrated. Conclusion: the configured
`AIwork4me@users.noreply.github.com` IS an existing noreply address of
the confirmed account — retained as the candidate author email
(preferred existing candidate per the mission; not a newly invented
address). `AIwork4me@qq.com` is a human-usable alternative the user may
substitute at submission time; either is legitimate.

## 3. DCO status: `DCO_ATTESTATION_PENDING` (deliberately unsigned)

What upstream actually requires (read from the frozen tree):
- `projects/miopen/CONTRIBUTING.md`: MIT-licensed contributions, branch
  + PR flow, two reviewers, regression test, issue association. **No
  DCO / Signed-off-by requirement stated.**
- Recent develop commits (7c58661..) carry **no** `Signed-off-by`
  trailers (squash-merged GitHub PRs).

However, a DCO sign-off is a *personal certification of the right to
submit under the license* — distinct from authorship. The user confirmed
authorship only. No statement in the Phase-5 authorization certifies:
(a) that the contribution is the user's original work / rightfully
held, and (b) agreement to certify under the DCO (or CLA if the
maintainers' bot requests one on the monorepo PR).

Therefore all three commits remain **unsigned**, each carrying the
explicit marker:

```text
DCO: PENDING HUMAN CONFIRMATION - provisional local commit, not for upstream submission; replace this line with a real Signed-off-by per DCO before submitting.
```

These are provisional local commits — NOT represented as signed. Exact
human action to finalize (if the user chooses to certify; replace the
marker line in each of the three commits):

```bash
cd /c/Users/rocm/Desktop/YOLO_AMD/rocm-libraries-phase5-candidate
git rebase -i 7c58661   # reword each commit: delete the "DCO: PENDING..." line and add exactly:
                        #   Signed-off-by: AIwork4me <AIwork4me@users.noreply.github.com>
```

(no explanatory text on the trailer line; author/committer identity
already correct). Then regenerate
`patches/phase5/canonical/*.patch` via `git format-patch 7c58661..HEAD`,
re-hash, and update `findings/phase5/PATCH_IDENTITY.json`. Commit SHAs
and patch hashes change — the submission checklist covers the follow-up
revalidation scope (metadata-only change: no tree bytes, so the source
validation remains applicable; regenerating patches is mandatory).

## 4. Copyright status: `COPYRIGHT_ATTRIBUTION_PENDING`

The FOUR new files carrying the placeholder MIT header retain
`Copyright (c) 2026 [contributor name and notice to be set by the submitter]`
(three kernel headers + the regression-test source
`projects/miopen/test/hiprtc_selfcontained.cpp` — Reviewer D caught the
fourth file).
Authorship (Git author = AIwork4me) does NOT establish legal copyright
ownership; the user has not (in this mission's authorization) asserted
it. Per the mission, if the user confirms AIwork4me holds the copyright,
fill exactly:

```text
Copyright (c) 2026 AIwork4me
```

in the FOUR files (3 kernel headers + `test/hiprtc_selfcontained.cpp`);
that changes validated bytes (comment-only,
classification COPYRIGHT_TEXT) → rerun the targeted validation
(CI matrix + DLL build + runtime spot-check) on the new candidate.

## 5. Checks performed on the final series

```text
git log -3 --format=fuller        — author/committer = AIwork4me <noreply>, correct subjects
git diff --check 7c58661..HEAD    — no whitespace errors
git show --stat (each)            — 8 files / 4+3 files / 2 files; scopes match subjects
git format-patch 7c58661..HEAD    — 3 patches, hashes in PATCH_IDENTITY.json
No placeholder author identity    — author is the confirmed AIwork4me
No synthetic copyright claims     — placeholders retained, PENDING
No provisional marker on any commit represented as signed — all three carry the marker; none claim sign-off
```
