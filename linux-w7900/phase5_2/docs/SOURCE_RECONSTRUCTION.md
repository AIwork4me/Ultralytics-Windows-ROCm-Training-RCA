# Source Reconstruction — Phase 5.2 (Gates B04/B05)

## Frozen upstream acquisition (B04)

* Target: `ROCm/rocm-libraries @ 7c5866144ac4b879be442563e2b49fa1c142ea36`
  (tree `8b0bf035e4568a1d994512b4346fed0dde3c591b`) — NOT the historical
  Phase-3 base `b68f8944` (tree `4da45589`).
* The unstable egress proxy blocked the full 1.2 GB codeload tarball and
  lazy promisor fetches. Acquisition chain used instead:
  1. commit+tree objects already local (blobless clone);
  2. the historical `source/upstream-pristine` extraction was WHOLE-TREE
     git-proven (`git add -A -f` + gitlink cacheinfo + `write-tree` ==
     `4da45589ff82934ab599b2fa818f443e25000767`, the exact b68f894 tree);
  3. its blobs were installed into the object store;
  4. the b68f894→7c586614 delta (886 paths) was computed locally;
  5. the 641 missing frozen-tree blobs were fetched through the
     AUTHENTICATED api.github.com contents endpoint, EACH verified by
     recomputed git blob SHA-1 before acceptance;
  6. final object-store inventory: 0 of 47,771 unique frozen-tree blobs
     missing; reachability pin `refs/phase52/frozen-base` created;
  7. worktree materialized via `worktree add --no-checkout` + `read-tree` +
     `checkout-index` (deterministic; slow-filesystem note recorded).
* Unresolved submodule gitlinks (by design, `BUILD_TESTING=OFF`):
  `projects/miopen/fin`, `projects/hipccl/hipccl3/libhipcxx`,
  `projects/rpp/third_party/ffts`,
  `shared/tensile/HostLibraryTests/googletest`.

## Exact candidate reconstruction (B05) — two independent methods

Both reproduce the frozen Windows head tree **exactly**:

| Method | Procedure | Result |
|---|---|---|
| A — `git am` | disposable sparse worktree @ frozen base; `git am` the 3 canonical patches in order | `HEAD^{tree}` = `605d0d214acdbc06086fdb27c61fec970c0f2798` |
| B — isolated index | disposable worktree @ frozen base; `read-tree HEAD`; `git apply --cached` ×3; `git write-tree` | tree = `605d0d214acdbc06086fdb27c61fec970c0f2798` |

Additional verified properties:

* exactly 3 commits from `git am`, author `AIwork4me
  <AIwork4me@users.noreply.github.com>` preserved from patch headers,
  subjects identical to `ordered_commit_subjects` (commit SHAs differ by
  committer identity — the tree is the content identity; matches Windows
  `git_am_roundtrip.json` note);
* `git diff --check` clean; all 10 changed paths under `projects/miopen`;
* the 10 changed files' git blob SHAs match the manifest's
  `changed_files_vs_base` 10/10 (recon tree vs manifest, both directions);
* the 4 new files carry `Copyright (c) 2026 AIwork4me`; no placeholders;
* no patched workload built or run; operational Leg B directories remain
  empty; disposable recon worktrees cleaned after evidence capture.

Independent audit: a fresh-context subagent re-performed BOTH methods in its
own worktrees from scratch with the same results.
