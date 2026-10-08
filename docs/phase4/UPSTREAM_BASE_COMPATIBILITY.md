# Upstream Base Compatibility (Gate P42)

Date: 2026-10-08. All observations made directly against
`ROCm/rocm-libraries` remote refs from the Windows machine
(blobless partial clone, blob bytes fetched on demand).

## Summary

```text
Validated baseline SHA : b68f8944300f104875d953fc8e4510908c9aaf0b
Current develop SHA   : 18e1985bb2a016c2e1f3d08227abae774f4598ca
Commit distance       : 37 commits (b68f894..18e1985)
Existing upstream fix : NONE FOUND
Patch applicability   : ordered series 0001 then 0002 applies CLEAN on develop
Decision              : PROCEED on baseline; no rebase performed or required
```

## Affected file drift

`git diff --stat b68f894 origin/develop -- <all eight patch-affected files>`
is EMPTY: upstream develop has made **zero changes** to:

- `projects/miopen/src/kernels/miopen_type_traits.hpp`
- `projects/miopen/src/kernels/miopen_utility.hpp`
- `projects/miopen/src/kernels/miopen_freestanding_type_traits.hpp` (does not exist upstream)
- `projects/miopen/src/kernels/miopen_freestanding_utility.hpp` (does not exist upstream)
- `projects/miopen/src/kernels/miopen_freestanding_initializer_list.hpp` (does not exist upstream)
- `projects/miopen/src/kernels/radix.hpp`
- `projects/miopen/src/kernels/tensor_view.hpp`
- `projects/miopen/src/CMakeLists.txt`

One upstream commit since the baseline touches a kernel inside the patch's
include closure but not any patched file:

- `eb209ed` fix(miopen): Restrict Welford DPP reduction to GFX9
  (ALMIOPEN-2838) (#12889) — modifies
  `projects/miopen/src/kernels/MIOpenBatchNormFwdTrainSpatial.cpp`
  (Welford DPP path only; include structure untouched).

## Equivalent-fix search

- `git grep -l freestanding origin/develop -- projects/miopen/src/kernels/`
  → no matches.
- `git grep -l __has_include origin/develop -- projects/miopen/src/kernels/`
  → no matches.
- `projects/miopen/src/kernels/miopen_type_traits.hpp` at `origin/develop`
  still has the same structure as at `b68f894`: in the HIP>=7 arm
  (lines 150–152) `#include <type_traits>` is reached with no
  runtime-compile guard, while the freestanding `namespace std`
  emulation only covers the HIP<7 arm (lines 145–149 are the legitimate
  HIP<7 offline arm). **The defect is still present upstream.**

## Patch applicability on current develop

Verified in a pristine detached worktree at `origin/develop`
(`rocm-libraries-phase4-develop-check`):

```text
git apply --check 0001            → applies clean
git apply 0001 && git apply --check 0002 → applies clean (ordered series)
```

Note: 0002 does NOT apply standalone on a clean tree (it depends on 0001);
this is expected for an ordered series and is not drift. Worktree was reset
and cleaned (`git status` empty) after the check.

## Contribution requirements observed (develop)

- Root `CONTRIBUTING.md`: standard ROCm monorepo flow; sparse-checkout and
  TheRock superbuild guidance; PRs to `develop`.
- `projects/miopen/CONTRIBUTING.md`:
  - all contributions under the MIT license;
  - no direct commits to develop — separate branch + PR;
  - two reviewers (one technical expert, one peer);
  - "For bugfixes and new features, new regression test created and
    included in CI" — motivates the Gate P47–P49 CI regression test;
  - "well-organized sequence of small commits" — matches the two-commit
    series design;
  - every PR associated with a ticket/issue (Phase-3 verified MIOpen
    issue #3956 open with the exact failure signature).
- `projects/miopen/test/` exists in the git tree at `develop` (resolved
  via git objects in this blobless worktree) but is absent from the
  on-disk sparse checkout; tests are wired by `add_subdirectory(test)`
  guarded by `BUILD_TESTING` in `projects/miopen/CMakeLists.txt:967-969`.
- `.clang-format` (repo root, Google-based, IndentWidth 4, ColumnLimit 100)
  and `projects/miopen/.clang-format` exist; formatting audit is Gate P54.

## Decision

No upstream equivalent fix exists; the validated baseline is 37 commits
behind develop with **zero drift** in all affected files; the ordered patch
series applies cleanly on develop. Per mission rules, no rebase was
performed — canonical commits are reconstructed on the validated baseline
`b68f894`. Applicability evidence above supports a future trivial rebase
at submission time if maintainers request it.
