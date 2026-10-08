# Reviewer A — Git / Patch Integrity Review (P5.1-CANDIDATE-R1)

- **Schema**: `phase5_1_review_v1`
- **Reviewer**: A-git-patch-integrity (adversarial)
- **Date**: 2026-10-08
- **Candidate**: P5.1-CANDIDATE-R1, 3-commit MIOpen series on frozen base `7c5866144ac4b879be442563e2b49fa1c142ea36` (ROCm/rocm-libraries develop)
- **Verdict**: **PASS**
- **Counts**: BLOCKER 0 · MAJOR 0 · MINOR 1 · NIT 3

Machine-readable twin: `findings/phase5_1/reviews/reviewer_A_git_patch_integrity.json`

---

## What I verified, adversarially, with my own commands

### 1. Commit order, parent chain, HEAD, base — PASS

- P5.1 worktree (`rocm-libraries-phase5.1-candidate`): HEAD = `e7ff6d75fac3e7b683e81e671555ada99af13b74`, tree = `605d0d214acdbc06086fdb27c61fec970c0f2798`, branch `prepare/miopen-hiprtc-phase5.1`, **clean** status.
- Chain (child→parent): `e7ff6d75` → `3b18a065` → `d4003de1` → **`7c586614` (base, exact)**. `git rev-list --count base..HEAD` = 3; zero merge commits; `git merge-base` = base; base equals the clone's `origin/develop` tip, so it is a genuine upstream develop commit.
- All three commits authored `AIwork4me <AIwork4me@users.noreply.github.com>`.

### 2. SHA256 domains — PASS (and stronger than asked)

Recomputed from bytes (not trusting the manifest):

| Patch | sha256 (recomputed) | Bytes | Manifest |
|---|---|---|---|
| 0001 | `14719b8b4ae7b4370afa42249b56c130d7d42b9447701e57a702570eb12ed7e2` | 15546 | match |
| 0002 | `7d40c314dcac87085178ba9d0c84bb2eced8f33ba8e9bd3a6151903d6ee4751e` | 7444 | match |
| 0003 | `3eb20ec0b4c38035438d317c210847e880ae8be5bf914617fb51f160f46670b4` | 27631 | match |

- Series concat (ordered `cat`, no separator) = `797a69b5ae86d0e304b2258b5f5323cc97241a413d2c43134bf01703f7842f6d` — matches manifest `series_hash`.
- **No CRLF**: `tr -cd '\r' | wc -c` = 0 for all three files; LF byte counts (406/170/651) equal line counts; last byte is `0x0A` in each. (An initial `grep -c $'\r'` reported hits — that is a known MSYS/ugrep false positive on this host; byte-level counting disproves it. Other reviewers should use `tr`, not grep, for this test.)
- **Stronger than a hash match**: I regenerated the patches with `git format-patch -o <tmp> d4003de1^..e7ff6d75` in the main clone — all three regenerated files are **byte-identical** to the canonical files (same sha256). The canonical patches are faithful, unedited `format-patch` products of exactly these commits.

### 3. P5 → P5.1 delta — PASS

- `git diff 29846fc4..e7ff6d75`: **exactly 4 files**, numstat `1/1` each, `4 files changed, 4 insertions(+), 4 deletions(-)`.
- Every hunk is the same comment-line replacement: ` * Copyright (c) 2026 [contributor name and notice to be set by the submitter]` → ` * Copyright (c) 2026 AIwork4me`, in `miopen_freestanding_initializer_list.hpp`, `miopen_freestanding_type_traits.hpp`, `miopen_freestanding_utility.hpp`, `test/hiprtc_selfcontained.cpp`. Nothing else differs.
- Commit messages **byte-identical** between series (sha256 of `%B`: `967d9e22…`/`e59db31f…`/`0cbf831c…` equal for all three P5↔P5.1 pairs).
- Author name/email identical; **author dates preserved exactly** (`13:37:28+08:00`, `14:40:01+08:00`, `14:40:01+08:00`). Committer dates differ (15:19:38–47) — explicitly permitted.

### 4. Historical immutability — PASS

- P5 worktree still at `29846fc4`, clean. `phase5-pristine` worktree still at `7c586614`, clean.
- P5 canonical patches still hash to `76fd6623…`, `d37376c9…`, `59306105…`; series concat `5ad951c716fbf986e627a94f65db679f4f49519d672912cb2e407bf3b714391d` — all equal the frozen documented values; regeneration from the P5 commits is also byte-identical. The tracked RCA blobs for these files equal the working bytes (no in-repo conversion).
- RCA repo `git status --short`: modified only `docs/phase5/` (4 files) + `findings/phase5/phase5_conclusion.json`; untracked `patches/phase5_1/`, `findings/phase5_1/`, `docs/phase5_1/`, `evidence/phase5_1/`, `scripts/phase5_1/`. **Nothing** under `patches/phase3|phase4`, `findings/phase3|phase4`, `docs/phase3|phase4` is touched.
- I read the phase5 doc diffs: they are annotated corrections (a `SUPERSEDED` banner and replacement of obsolete pre-amendment commit IDs/hashes with the current P5 values). I verified the *new* values against the actual immutable patch bytes — they match — and the discarded values are retained in `evidence/phase5_1/consistency/pre_fix_findings.json` / `post_fix_verification.json` (both present). This is legitimate errata handling, not evidence tampering; the patch bytes themselves never changed.

### 5. Source-tree reconstruction — PASS

- Fresh temp worktree at base `7c586614` in the main clone; `git am` of the three canonical patches applied cleanly (exit 0); resulting `HEAD^{tree}` = **`605d0d214acdbc06086fdb27c61fec970c0f2798`**, exactly the candidate HEAD tree. Authors/dates/subjects reproduce from the patch headers.
- Temp worktree removed and `worktree list` re-verified afterwards.

### 6. Patch-envelope validity — PASS

- Each file carries a proper `From <full-sha> Mon Sep 17 00:00:00 2001` line referencing exactly `d4003de1`/`3b18a065`/`e7ff6d75`; `From:`, `Date:` (equal to the commit author dates), `Subject: [PATCH n/3]` headers; `diff --git` + `index` lines; trailing signature `2.55.0.windows.5`. File sections per patch: 5 / 4 / 2 = 10 unique files = the manifest's `changed_files_vs_base`.
- Sequential `git apply --check` on the byte-exact base (after applying prior patches with `--index`) succeeded for all three; `git apply --index` of all three yields `git write-tree` = `605d0d21…` again — a second, non-`am` reconstruction path to the same tree.
- Note: one initial `apply --check` of patch 3 failed with "No such file or directory" for `projects/miopen/test/CMakeLists.txt` — my temp worktree had inherited the clone's **sparse-checkout** cone (`projects/miopen/src/kernels` only; file present in index with skip-worktree). After widening the cone, everything passes. Environmental artifact of my own test rig, not a patch defect; `git am`/`--index` application never needed the worktree copy.

### 7. Manifest vs reality — PASS

Every identity in `findings/phase5_1/FINAL_HANDOFF.json` that falls in my domain matches my recomputation: `ordered_commits`, `ordered_commit_subjects`, `ordered_patches` (paths + sha256 + byte counts), `series_hash`, `base_sha`, `head_tree_sha1` (verified by two independent reconstructions), all **10** `git_blob` values in `changed_files_vs_base` (exact `git ls-tree` match), and `supersedes.phase5_commits` (equal to the actual P5 branch commits).

### 8. No force-push / history rewrite — PASS

- `git branch -a -v`: `develop b68f8944`, `prepare/miopen-hiprtc-phase5 29846fc4`, `prepare/miopen-hiprtc-phase5.1 e7ff6d75`, `prepare/miopen-hiprtc-selfcontained 4084759f`; the only remote branch is `origin/develop` at `7c586614`. No phase5/5.1 branch exists on any remote — nothing was ever pushed, so no force-push is possible.
- Reflogs corroborate the documented construction: `prepare/miopen-hiprtc-phase5.1` created from `7c586614` at 15:19:05 +0800, then built by cherry-pick + amend per commit (exactly the "rebuild with one change" story); the phase5 branch tip has not moved since its final commit; the phase4 branch reflog is untouched since creation. The amends are the P5.1 build itself, not a rewrite of frozen history — and the byte-exact 4-line delta (check 3) proves the amends introduced nothing else.

### 9. DCO posture — PASS

- `grep '^Signed-off-by:'` over `%B` of all six commits (P5 and P5.1): **0 hits**.
- All three P5.1 commits (and all three patch files, exactly once each) carry: `DCO: PENDING HUMAN CONFIRMATION - provisional local commit, not for upstream submission; replace this line with a real Signed-off-by per DCO before submitting.` Consistent with `dco_status` in the manifest.

---

## Findings

### A-1 (MINOR) — .gitattributes byte-exactness rules do not cover `patches/**`

The RCA repo has `core.autocrlf=true` and `.gitattributes` with `* text=auto`, plus explicit `-text` no-conversion overrides for `evidence/raw/**` and `evidence/phase2/**` **only**. `patches/phase5_1/canonical/*.patch` are currently untracked, and I verified the already-tracked `patches/phase5/canonical/*.patch` blobs are stored byte-identical to the working files — so there is **no current corruption**. But if the phase5_1 patches are committed under the current attributes, a future fresh checkout on Windows would smudge them to CRLF, and the working-tree bytes would no longer match the SHA256 values frozen in `FINAL_HANDOFF.json` (breaking any `sha256sum -c` style gate).
**Resolution**: add `patches/** -text` to `.gitattributes` before committing the phase5_1 artifacts; re-verify the three hashes from a fresh checkout.

### A-2 (NIT) — `format-patch --stdout` reproduction differs from the series concat by exactly 2 bytes

`git format-patch --stdout d4003de1^..e7ff6d75` = 50623 bytes (sha256 `85434328…`) vs the canonical concat 50621 bytes (`797a69b5…`); `cmp` locates the difference at byte 15547 — stdout emits one extra `0x0A` after patch 1's signature (and after patch 2's). Per-file regeneration (`-o`) is byte-identical, so the manifest's file-concat definition is unambiguous and correct; only a future reproducer using `--stdout` would see a confusing mismatch.
**Resolution**: document that regeneration must use per-file output, not `--stdout`.

### A-3 (NIT) — `patches/phase5_1/canonical/` has no README.md

`patches/phase5/canonical/` and `patches/phase4/canonical/` each carry a README; `patches/phase5_1/` contains only `canonical/` with the three patches. No integrity impact.
**Resolution**: optionally add a README pointing at `findings/phase5_1/FINAL_HANDOFF.json`.

### A-4 (NIT) — RCA phase5_1 artifacts are still untracked

`patches/phase5_1/`, `findings/phase5_1/`, `docs/phase5_1/`, `evidence/phase5_1/`, `scripts/phase5_1/` are untracked; until committed, the frozen evidence chain lives only in the working tree.
**Resolution**: commit after applying A-1.

---

## Verdict

**PASS.** Every challengeable identity in the handoff survived independent recomputation, two independent reconstruction paths (`git am` and `git apply --index` + `write-tree`) reproduce the candidate tree byte-exactly from base + patch bytes, the P5 predecessor and all earlier phases are provably untouched, no history was rewritten or pushed, no `Signed-off-by` exists anywhere, and the DCO-pending marker is present on all three commits. The one MINOR finding is a *future-risk* hygiene item (`.gitattributes` coverage for `patches/**`), not a defect in the candidate as it stands.
