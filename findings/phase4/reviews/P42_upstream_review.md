# Gate P42 Review — Upstream Base Compatibility (Phase 4)

Reviewer: independent verification agent (ZCode), 2026-10-08.
Document under review: `docs/phase4/UPSTREAM_BASE_COMPATIBILITY.md`.
Method: direct read-only observation against the `ROCm/rocm-libraries` git repo
(blobless partial clone; commands run from the `rocm-libraries-phase4-develop-check`
worktree, detached at `origin/develop`). The phase3 worktree was not modified.
The develop-check worktree was left pristine (verified at the end).

## VERDICT: PASS

All six verification points confirmed by independent observation. Two NIT-level
wording issues only; no BLOCKER, MAJOR, or MINOR findings.

## Findings

- **BLOCKER**: none.
- **MAJOR**: none.
- **MINOR**: none.
- **NIT-1** (doc line 48): the doc says the unguarded
  `#include <type_traits>` sits "at the `#else`/HIP>=7 arm (lines 145–152)".
  The HIP>=7 `#else` arm is precisely lines 150–152; lines 145–149 are the
  HIP<7 / not-`MIOPEN_HIP_RUNTIME_COMPILE` (offline-compile) arm, whose
  `#include <type_traits>` (line 147) is legitimate. Substance of the claim
  (unguarded include in the HIP>=7 arm reachable under runtime compilation)
  is correct; only the line-range wording is loose.
- **NIT-2** (doc lines 80–84): the paragraph "projects/miopen/test/ does not
  exist at develop HEAD as a checkout path" is accurate but easy to misread as
  "absent from the tree". In fact `git ls-tree origin/develop
  projects/miopen/test/` lists 58 entries; only the on-disk sparse/blobless
  checkout omits the directory. The doc does state this; consider rewording
  "does not exist at develop HEAD as a checkout path" → "is not checked out
  on disk in this worktree".

## Evidence

All commands run in `C:\Users\rocm\Desktop\YOLO_AMD\rocm-libraries-phase4-develop-check`
(Git Bash) unless noted.

### 1. SHAs and commit distance — CONFIRMED

```
$ git rev-parse origin/develop
18e1985bb2a016c2e1f3d08227abae774f4598ca
$ git rev-parse b68f8944300f104875d953fc8e4510908c9aaf0b
b68f8944300f104875d953fc8e4510908c9aaf0b
$ git rev-list --count b68f894..origin/develop
37
```

Baseline SHA resolves; develop SHA matches the doc; distance is exactly 37.

### 2. Affected-file drift — CONFIRMED EMPTY

```
$ git diff --stat b68f894 origin/develop -- \
    projects/miopen/src/kernels/miopen_type_traits.hpp \
    projects/miopen/src/kernels/miopen_utility.hpp \
    projects/miopen/src/kernels/miopen_freestanding_type_traits.hpp \
    projects/miopen/src/kernels/miopen_freestanding_utility.hpp \
    projects/miopen/src/kernels/miopen_freestanding_initializer_list.hpp \
    projects/miopen/src/kernels/radix.hpp \
    projects/miopen/src/kernels/tensor_view.hpp \
    projects/miopen/src/CMakeLists.txt
(no output; exit 0)
```

Cross-check by blob OID (stronger than diff-stat — proves byte identity, not
just net-zero diff):

```
miopen_type_traits.hpp: baseline=e2b6a98e... develop=e2b6a98e... same=YES
miopen_utility.hpp:     baseline=156cb30f... develop=156cb30f... same=YES
radix.hpp:              baseline=f8a91fed... develop=f8a91fed... same=YES
tensor_view.hpp:        baseline=36ddef6d... develop=36ddef6d... same=YES
CMakeLists.txt (src/):  baseline=19dce8c1... develop=19dce8c1... same=YES
```

The three freestanding headers do not exist upstream at develop:

```
$ for f in miopen_freestanding_type_traits.hpp miopen_freestanding_utility.hpp \
           miopen_freestanding_initializer_list.hpp; do \
    git cat-file -e origin/develop:projects/miopen/src/kernels/$f \
    && echo EXISTS || echo absent; done
absent / absent / absent
```

### 3. No equivalent upstream fix; defect still present — CONFIRMED

```
$ git grep -l freestanding origin/develop -- projects/miopen/src/kernels/
(no matches; exit 1)
$ git grep -l __has_include origin/develop -- projects/miopen/src/kernels/
(no matches; exit 1)
```

`origin/develop:projects/miopen/src/kernels/miopen_type_traits.hpp` (152
lines; blob identical to baseline, see §2) preprocessor structure:

```
28:#if HIP_PACKAGE_VERSION_FLAT < 7000000000ULL
29:#ifdef MIOPEN_HIP_RUNTIME_COMPILE
31-144:  namespace std { ... freestanding emulation ... }
145:#else                 # HIP<7, offline compile
147:  #include <type_traits>   (legitimate: offline compiler has host headers)
149:#endif
150:#else                 # HIP>=7 arm — applies REGARDLESS of runtime-compile mode
151:  #include <type_traits>   # UNGUARDED for runtime-compiled (HIPRTC) kernels
152:#endif
```

Under HIP>=7 + `MIOPEN_HIP_RUNTIME_COMPILE` the HIP<7 freestanding emulation is
skipped and line 151's host-side `#include <type_traits>` is reached with no
`MIOPEN_HIP_RUNTIME_COMPILE` guard — the defect the patches fix. Defect present
at develop. (Doc's "lines 145–152" wording: see NIT-1.)

### 4. Ordered-series applicability — CONFIRMED

Patches extracted as blob bytes from the RCA repo
(`C:\Users\rocm\Desktop\YOLO_AMD\Ultralytics-Windows-ROCm-Training-RCA`):

```
$ git -C <RCA> cat-file blob origin/main:patches/phase3/0001-miopen-hiprtc-selfcontained.patch
$ git -C <RCA> cat-file blob origin/main:patches/phase3/0002-miopen-hiprtc-selfcontained.patch
```

0001 touches exactly: miopen_type_traits.hpp, miopen_utility.hpp,
src/CMakeLists.txt, + new miopen_freestanding_{type_traits,utility}.hpp.
0002 touches exactly: radix.hpp, tensor_view.hpp, src/CMakeLists.txt,
+ new miopen_freestanding_initializer_list.hpp. Union = the eight files of §2.

In the pristine develop-check worktree (`git status` empty beforehand, detached
at 18e1985):

```
$ git apply --check p42_0001.patch          → exit 0
$ git apply p42_0001.patch                  → exit 0
  (status: M CMakeLists.txt, M type_traits, M utility, ?? 2 freestanding files)
$ git apply --check p42_0002.patch          → exit 0
```

Restoration (per review protocol):

```
$ git reset --hard HEAD && git clean -fd projects/miopen/src/kernels/
HEAD is now at 18e1985 hipBlasLt UG (#12267)
Removing ... miopen_freestanding_type_traits.hpp
Removing ... miopen_freestanding_utility.hpp
$ git status --short                        → (empty)
```

Doc's side claim re-checked: 0002 standalone on a clean develop tree fails —
`error: projects/miopen/src/CMakeLists.txt: patch does not apply` (exit 1) —
consistent with an ordered series that depends on 0001's CMakeLists hunk.
Temp patch files deleted after review.

### 5. eb209ed touching MIOpenBatchNormFwdTrainSpatial.cpp — CONFIRMED

```
$ git log --oneline b68f894..origin/develop -- \
    projects/miopen/src/kernels/MIOpenBatchNormFwdTrainSpatial.cpp
eb209ed fix(miopen): Restrict Welford DPP reduction to GFX9 (ALMIOPEN-2838) (#12889)
```

Only commit in range touching that file. Its diff to the file changes two
`if constexpr` conditions (`use_amdgcn` → `use_gfx9_dpp`); grep over the whole
commit finds zero `+/-#include` lines. "Welford DPP path only; include
structure untouched" is accurate. (The commit also touches 5 other kernel
files — BatchNormActivBwdSpatial, BatchNormBwdSpatial, configuration.hpp,
default_configurations.hpp, reduction_functions.hpp — none of which is a
patched file; doc's scoping claim holds.)

### 6. Contribution-requirements summary — CONFIRMED ACCURATE

Root `CONTRIBUTING.md` at develop: sparse-checkout clone guidance and TheRock
"preferred system for performing a superbuild" present; branching model keeps
`develop` as the integration branch (develop → staging → mainline → release).

`projects/miopen/CONTRIBUTING.md` at develop, line-verified:

- line 30: "All contributions you make will be under the [MIT Software License]".
- lines 67–70: "No changes are allowed to be directly committed to the develop
  [branch] ... separate branch and then create a pull request (PR)".
- lines 72–78: two reviewers — first a technical expert, second a peer.
- line 97 (reviewer checklist #2): "well-organized sequence of small commits".
- line 108 (checklist #5): "For bugfixes and new features, new regression test
  created and included in CI".
- line 110 (checklist #6): "Is every PR associated with a ticket or issue
  number for tracking purposes?".

Cross-checks: `if(BUILD_TESTING) add_subdirectory(test)` confirmed at exactly
lines 967–969 of `projects/miopen/CMakeLists.txt` at develop. Root
`.clang-format`: `BasedOnStyle: Google`, `IndentWidth: 4`, `ColumnLimit: 100`.
`projects/miopen/.clang-format` exists. `projects/miopen/test/` exists in the
develop tree (58 entries via `git ls-tree`) but is not on disk in this sparse
worktree — matches the doc (see NIT-2 on wording).

## Required actions

None blocking. Optional (cosmetic, may be folded into any later doc edit):

1. Correct the HIP>=7 arm line reference from "145–152" to "150–152" (NIT-1).
2. Reword the `projects/miopen/test/` sentence to make clear the directory
   exists in the develop tree but is not checked out on disk (NIT-2).

The doc's decision logic (PROCEED on baseline b68f894, no rebase, ordered
series applies cleanly on current develop) is fully supported by the evidence
above.
