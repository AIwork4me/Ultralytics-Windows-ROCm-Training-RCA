# P5-02 Independent Upstream-Base Review (Upstream Drift Re-verification)

- Reviewer: independent upstream-drift reviewer (Phase 5), working from own commands only.
- Date: 2026-10-08 (local machine time).
- Artifact under review: `docs/phase5/UPSTREAM_BASE_ASSESSMENT.md` (RCA repo, branch
  `phase5/windows-final-upstream-prep`).
- Repos used:
  - Upstream: `C:\Users\rocm\Desktop\YOLO_AMD\rocm-libraries-phase3` (git dir, blobless
    partial clone of `https://github.com/ROCm/rocm-libraries.git`, worktrees
    `rocm-libraries-phase4-{baseline,canonical,develop-check}`).
  - RCA: `C:\Users\rocm\Desktop\YOLO_AMD\Ultralytics-Windows-ROCm-Training-RCA`.

## Verdict

**PASS** — every material claim in `UPSTREAM_BASE_ASSESSMENT.md` was independently
reproduced. Findings: 0 BLOCKER, 0 MAJOR, 1 MINOR, 2 NIT.

## Findings table

| # | Severity | Finding | Disposition |
|---|---|---|---|
| F1 | MINOR | The assessment's statement "working-tree copies are CRLF-smudged, MUST use `git cat-file blob`" was verified and is *necessary*: working-tree `0001` is 15,547 bytes vs blob 15,143 (+404 CR); `0002` is 6,531 vs 6,375 (+156 CR). Anyone re-running the apply from working-tree copies on a different smudge configuration could get spurious failures. | Documented correctly in the assessment; method is sound. No action required; consider also noting the exact byte deltas for auditability. |
| F2 | NIT | Assessment section 4 says "9 files, none conflicting" and lists `test/gtest/cache.cpp` among them; the section-4 headline says "MIOpen-wide drift ... 9 files" while the table in section 2 speaks of 8 affected files — the 9 vs 8 distinction (upstream drift files vs patch-affected files) is correct but easy to misread. | Editorial only. Verified: exactly 9 files changed under `projects/miopen/`, none of them among the 8 patch-affected files. |
| F3 | NIT | `git log --grep` over the range with keywords RTC/HIPRTC/STL/self-contained matches 7 commits, all false positives ("robu**stl**y", "co**stl**y", "hone**stl**y", rocFFT `rtc_bluestein`, hipdnn-integration-tests HipRTC reference kernel, rocke self-contained helpers package). A naive re-runner may think an equivalent fix exists. | Not a defect in the assessment (its conclusion "no equivalent fix" is correct); recorded here so future re-runs don't misread keyword hits. |

No BLOCKER or MAJOR findings. All five verification tasks below reproduce the
assessment's results exactly.

## 1. Develop position after fresh fetch

Commands (in `rocm-libraries-phase3`):

```
$ git fetch origin develop
From https://github.com/ROCm/rocm-libraries
 * branch            develop    -> FETCH_HEAD
$ git rev-parse origin/develop FETCH_HEAD
7c5866144ac4b879be442563e2b49fa1c142ea36
7c5866144ac4b879be442563e2b49fa1c142ea36
$ git log -1 --format='%H %ci %s' origin/develop
7c5866144ac4b879be442563e2b49fa1c142ea36 2026-10-07 21:59:34 -0600 csrmv LRB: fix unsigned 32-bit overflow in grid_size (AISPARSE-662) (#11215)
```

- The fetch contacted GitHub (no update line printed → remote develop unchanged).
- **origin/develop == 7c586614... (frozen value). Develop has NOT moved past 7c58661.**
- No new commit exists since the freeze, hence none can touch
  `projects/miopen/src/kernels` or the 8 affected files.
- Also verified the assessment's Phase-4 observation: `18e1985` is an ancestor of
  `7c58661`; `git log --oneline 18e1985..7c58661 | wc -l` → **7 commits**
  (csrmv/rocBLAS/AISPARSE/hipdnn/fft/hipblaslt), and
  `git log 18e1985..7c58661 -- projects/miopen/ | wc -l` → **0**. Matches the claim
  "advanced by 7 commits, none touch projects/miopen/".

## 2. Duplicate / equivalent-fix detection — reproduced NEGATIVE

```
$ git grep -l __has_include origin/develop -- projects/miopen/src/kernels/
(empty, exit 1)
$ git ls-tree -r --name-only origin/develop -- projects/miopen/src/kernels/ | grep -i freestanding
(empty, exit 1)
$ git log --oneline b68f894..origin/develop -- projects/miopen/
eb209ed fix(miopen): Restrict Welford DPP reduction to GFX9 (ALMIOPEN-2838) (#12889)
d2aaf8c ALMIOPEN-2598: Reuse KernDb connections via cached-database mechanism (#11933)
```

- Only **2 commits** touch `projects/miopen/` in the whole `b68f894..origin/develop`
  range; neither subject mentions RTC/HIPRTC/STL/type_traits/freestanding.
- Keyword sweep `git log -i --grep` (RTC/HIPRTC/type_traits/freestanding/
  self-contained/selfcontained/STL) over the range matched 7 commits; full-message
  inspection shows all are false positives (see F3): substring hits on "robustly /
  costly / honestly / TestLlvm", plus genuinely unrelated scopes (rocFFT bluestein
  RTC kernels, hipdnn-integration-tests GPU-reference HipRTC kernel, rocke helpers
  "self-contained package", i.e. `dnn-providers/hip-kernel-provider/rocke/...`).
- `__has_include` does exist elsewhere in MIOpen at both bases
  (`src/demangle.cpp`, `src/include/miopen/filesystem.hpp`) — pre-existing host-side
  files, unchanged in the range, no interaction with kernels.
- **Confirmed: no equivalent fix landed upstream.**

## 3. Affected-file blob OIDs — ZERO drift in all 8 files (reproduced)

```
$ for f in <5 existing files>: git ls-tree <b68f894|7c58661> -- $f
SAME e2b6a98e... projects/miopen/src/kernels/miopen_type_traits.hpp
SAME 156cb30f... projects/miopen/src/kernels/miopen_utility.hpp
SAME f8a91fed... projects/miopen/src/kernels/radix.hpp
SAME 36ddef6d... projects/miopen/src/kernels/tensor_view.hpp
SAME 19dce8c1... projects/miopen/src/CMakeLists.txt
$ git ls-tree -r --name-only origin/develop -- projects/miopen/src/kernels/ | grep freestanding
(empty)  → miopen_freestanding_{type_traits,utility,initializer_list}.hpp absent upstream
```

All five pre-existing files have identical blob OIDs at `b68f894` and `7c58661`;
the three freestanding files do not exist at `origin/develop`. Matches the claim.

## 4. Sequential patch application on a fresh detached worktree @ 7c58661 — CLEAN (reproduced)

Method (blob bytes, per the CRLF-smudge trap — trap itself verified, see F1):

```
blob sha256 0001 = f06d7ae5d87f73e102c10a4e985afde70659210b96e5ad3247eeea85f4568e20 (15,143 B, 0x0D count = 0)
blob sha256 0002 = 77f9fc1613695b849a5b04e59723c05482467ddc34d0a9d53bf3cdd31f761532 ( 6,375 B, 0x0D count = 0)
working-tree copies: 15,547 B / 6,531 B → CRLF-smudged; NOT used.
```

Fresh worktree (created and removed by this reviewer):

```
$ git worktree add --detach --no-checkout .../tmp_p502_review_wt 7c58661
$ git sparse-checkout set projects/miopen/src && git checkout   # clean status
$ git apply --check p0001 → OK;  git apply p0001 → OK
$ git add -A; compare staged OIDs vs c86d1b95:
  SAME a2be3a29 CMakeLists.txt / 983cdfe1 miopen_type_traits.hpp / 770882ae miopen_utility.hpp
  SAME 40bd307d miopen_freestanding_type_traits.hpp / f335261b miopen_freestanding_utility.hpp  (5/5)
$ git apply --check p0002 → OK;  git apply p0002 → OK
$ git add -A; compare staged OIDs vs 4084759: 8/8 SAME
  ... + 99c29fda radix.hpp / d7963324 tensor_view.hpp / 79498fd8 miopen_freestanding_initializer_list.hpp
$ git diff 4084759 --stat -- projects/miopen/src/  → only the 8 upstream drift files
  (kern_db, sqlite_db, BatchNorm trio, configuration, default_configurations,
   reduction_functions), i.e. exactly upstream's own b68f894..7c58661 drift.
```

Canonical chain sanity: `c86d1b95` parent = `b68f894`; `4084759` parent = `c86d1b95`
(`git log --format='%H %P' -2 4084759`).

**Result: sequential application of the exact blob-byte patches on a detached
worktree at 7c58661 yields staged content byte-equal (LF-normalized, blob-OID
equality) to Phase-4 canonical c86d1b95 (after 0001) and 4084759 (after 0002),
8/8 files.** Matches the claim, including the note that a single
`git apply --check p1 p2` invocation is invalid methodology (0002 depends on 0001).

Note: `core.autocrlf=false` in the repo and `projects/miopen/.gitattributes`
(only `*.db.bz2/*.kdb`/bin attributes) impose no eol smudge on the affected files,
so the worktree checkout was exact LF and `git apply` operated on pristine bytes.

## 5. Challenge — could anything in b68f894..origin/develop -- projects/miopen/ invalidate the patch?

Drift = exactly 9 files (matches assessment section 4):

```
projects/miopen/src/include/miopen/kern_db.hpp            (d2aaf8c)
projects/miopen/src/include/miopen/sqlite_db.hpp          (d2aaf8c)
projects/miopen/src/kernels/MIOpenBatchNormActivBwdSpatial.cpp (eb209ed)
projects/miopen/src/kernels/MIOpenBatchNormBwdSpatial.cpp     (eb209ed)
projects/miopen/src/kernels/MIOpenBatchNormFwdTrainSpatial.cpp(eb209ed)
projects/miopen/src/kernels/configuration.hpp             (eb209ed)
projects/miopen/src/kernels/default_configurations.hpp    (eb209ed)
projects/miopen/src/kernels/reduction_functions.hpp       (eb209ed)
projects/miopen/test/gtest/cache.cpp                      (d2aaf8c)
```

Checks performed:

1. **Macro conflicts**: `git grep -n MIOPEN_FREESTANDING origin/develop -- projects/miopen/`
   → empty. Nothing defines or references `MIOPEN_FREESTANDING_TRAITS_ACTIVE`
   (the only new guard macro introduced by 0001) upstream. No conflict.
2. **New STL includes in kernels**: `git grep -n -E '#include *<(type_traits|utility)>' origin/develop -- projects/miopen/src/kernels/`
   → only `miopen_type_traits.hpp` (2x) and `miopen_utility.hpp` (2x), i.e. exactly
   the pre-existing include lines the series wraps with `__has_include`; both files
   are blob-identical across the two bases. No other kernel gained an STL include.
3. **Include-closure of the CI regression kernel**: `MIOpenBatchNormFwdTrainSpatial.cpp`
   `#include` list is byte-identical (same 8 lines, lines 8–15) at `b68f894` and
   `7c58661` (verified with `git show <rev>:<file> | grep '#include'`). The
   eb209ed changes are `use_amdgcn` → `use_gfx9_dpp` macro/logic renames:
   `git show eb209ed | grep -E '^[+-]#include'` → no include lines changed in any of
   the six kernel files. The compile surface of the regression test is unaffected.
4. **Consumers of tensor_view.hpp / radix.hpp**: consumers at origin/develop are
   `src/CMakeLists.txt`, `src/include/miopen/tensor_view_utils.hpp`,
   `hipconv/*`, and kernel cpps (MIOpenGetitem/Kthvalue/MultiMarginLoss/PReLU/
   ReduceSum/SoftMarginLoss for tensor_view; MIOpenKthvalue for radix). **None of
   these files changed in the drift range** (the 9 drift files contain zero
   references to tensor_view/radix — verified by grep over each drift file's
   content at 7c58661).
5. **KernDb (hipRTC compile path)**: d2aaf8c's kern_db.hpp/sqlite_db.hpp hunks are
   SQLite connection reuse + lock-scope changes only; grep of the diff for
   include/compile/flag/hiprtc/header/option/`-I` content lines → nothing. Kernel
   compilation flags and RTC source handling unchanged.
6. **Outside projects/miopen**: the full-range diff (886 files) is dominated by
   `dnn-providers/hip-kernel-provider` (separate "rocke" subproject), hipblaslt
   tuning data, and CI workflow tweaks — none consumed by MIOpen's kernel build.

**No change in the range can make the validated patch series ineffective or wrong.**

## Conclusion

- Develop frozen at `7c5866144ac4b879be442563e2b49fa1c142ea36`: **confirmed still current**
  (fresh fetch; no movement).
- Zero drift in the 8 affected files between `b68f894` and `origin/develop`: **confirmed**.
- No equivalent fix upstream: **confirmed**.
- Ordered two-patch series applies clean sequentially at `7c58661` producing content
  byte-equal to Phase-4 canonical `c86d1b95` / `4084759`: **confirmed on a fresh
  detached worktree created and destroyed by this reviewer**.
- No macro/include/closure/consumer conflict in `b68f894..origin/develop -- projects/miopen/`:
  **confirmed**.

**Verdict: PASS.** The assessment's "CLEAN — proceed with frozen develop 7c58661"
stands. Biggest residual risk is procedural, not technical: the patches only
reproduce from `git cat-file blob` bytes; the CRLF-smudged working-tree copies
(verified: +404/+156 CR bytes) will mislead anyone who re-runs the apply from disk
without the blob-extraction step.
