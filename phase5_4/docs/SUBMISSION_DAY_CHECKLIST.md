# SUBMISSION DAY CHECKLIST — Phase 5.4 (for the human who submits)

Print/state each item before creating the upstream PR. Nothing here authorizes submission by itself; it exists so the authorized human starts from a verified state.

## 0. Authorization preconditions (human-only)

- [ ] Explicit go-ahead given for creating the PR on `ROCm/rocm-libraries` (this mission's standing boundary: `UPSTREAM_SUBMISSION = NOT_AUTHORIZED` until then).
- [ ] DCO decision recorded. Current finding: upstream `CONTRIBUTING.md` (root + `projects/miopen`) has **no** DCO/Signed-off-by requirement; commits are deliberately unsigned. If you choose to sign anyway, `git rebase --exec 'git commit --amend --no-edit -s'`-style rewriting changes commit SHAs — re-run the identity steps below afterwards.
- [ ] Copyright holder `AIwork4me` (© 2026, MIT) still truthful.

## 1. Refresh upstream develop (mandatory — a stale base is the #1 submission-day risk)

- [ ] `git fetch origin develop` in the rocm-libraries clone.
- [ ] If `origin/develop` is still `681bc9edc37e8ceceb1c8227d8e63fc2ea9f5243`: base unchanged, proceed.
- [ ] If it moved: re-run the ten-file blob audit (`git rev-parse <newtip>:<path>` vs the six upstream files' blobs at `681bc9ed`):
  - all six identical AND the four R2 files still absent → rebase/replay is expected clean; re-run at minimum the regression-test build + ctest gate before submitting, and republish identities.
  - any file changed → **stop**; re-run Gate P54-01/P54-02-style analysis before any submission.
- [ ] Watch open PRs #10945 (touches `src/CMakeLists.txt`) and #10426 (touches closure file `batchnorm_functions.hpp`) for merges that would create conflicts; also #12733 (disjoint files, but same area).

## 2. Verify candidate state

- [ ] Local branch `miopen/hiprtc-freestanding-upstream-ready` = `cab3f08ab406a3567c2483904b137f3715d00db2` (three commits on `681bc9ed`).
- [ ] `git diff --stat 681bc9ed cab3f08a` = 10 files, +1036/−5.
- [ ] Series SHA256 (`sha256` of concatenated `phase5_4/patches/prospective_submission_series/*.patch`) = `8e00f59114d17205d06664a065856bbd9012e40065e8826e4725f790c024a0c5`; payload identical to R2 series `48308f6d…`.

## 3. PR creation mechanics

- [ ] Push the branch to the AIwork4me **fork** (create fork only when submitting — `gh repo fork ROCm/rocm-libraries --clone=false`); never push to ROCm remotes.
- [ ] Open PR `ROCm/rocm-libraries:develop` ← fork branch.
- [ ] Title: `MIOpen: make HIPRTC kernel includes self-contained without host STL`.
- [ ] Body: copy `phase5_4/docs/UPSTREAM_PR_DRAFT_FINAL.md` (verify every hash/link one final time against this branch's evidence manifest).
- [ ] `Fixes ROCm/MIOpen#3956` must appear in the **full cross-repo form** (closing keywords work cross-repo only in that form and only into the default branch `develop`).
- [ ] Do not add `Signed-off-by` unless the DCO decision changed.

## 4. Post-PR expectations

- [ ] Linux CI will show `test_hiprtc_selfcontained` as **Skipped/Not Run** on stock runners — that is correct behavior (probe-documented); be ready to point at the PR's Regression Test section.
- [ ] Windows no-STL coverage does not exist in upstream CI yet — the PR's Windows evidence is this RCA; a maintainer may ask for CI enablement separately.
- [ ] If maintainers request changes to the test registration (e.g., shared-helper refactor), that is a **new candidate revision** — re-run the Windows validation cycle before pushing again.

## 5. After submission (bookkeeping)

- [ ] Record PR URL in the RCA repo; update memory of mission status.
- [ ] Never rewrite the frozen branches: `phase5.1/windows-r2-ci-portability-freeze` @ `c841716`, `linux-w7900/phase5.3-r2-final-ab` @ `166c33d`.
