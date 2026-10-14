# Source Provenance — PR #13437 final HEAD `f0f330c4`

## Upstream identity (verified 2026-10-15, read-only GitHub API)

- PR: https://github.com/ROCm/rocm-libraries/pull/13437 (open, not merged)
- PR `head.sha` = `f0f330c4837a3c4ca9736a8059410cca1a7c2b85`
  = contributor branch `fix/miopen-hiprtc-no-host-stl` head in
  `AIwork4me/rocm-libraries` (branch head queried independently, same SHA)
- Commit series (2 commits on base `develop` @ `b8cf0e7b526f4a25c0623f5b2a4fe41e03ede179`):
  - `c6ed813117599081cd3c6138016adcdb4308c6a0` — source fix (parent `b8cf0e7b`, verified)
  - `f0f330c4837a3c4ca9736a8059410cca1a7c2b85` — regression gtest
- PR diff vs base: **7 files, +376 / −61** (see `pr_diffstat.txt` excerpt below)

```text
 projects/miopen/src/CMakeLists.txt                 |   1 +
 .../miopen/src/kernels/miopen_initializer_list.hpp |  45 +++++
 .../miopen/src/kernels/miopen_type_traits.hpp      | 151 ++++++++++-----
 .../miopen/src/kernels/miopen_utility.hpp          |  25 +--
 .../miopen/src/kernels/radix.hpp                   |   9 +-
 .../miopen/src/kernels/tensor_view.hpp             |   2 +-
 .../miopen/test/gtest/hiprtc_selfcontained.cpp     | 204 +++++++++++++++++++
```

## Source-to-binary chain

1. **Git commit → worktree**: a dedicated worktree at `C:\w56` holds branch
   `fix/miopen-hiprtc-no-host-stl` at `f0f330c4`. `git status --porcelain`
   was **empty immediately before configure and after the build** (captured
   in `raw/provenance/w56_status_before_build.txt` — zero lines — and
   `raw/provenance/w56_head.txt`; the build ran from
   `C:/w56/projects/miopen`; the tree re-verified clean after all runs).
2. **Worktree → binary**: fresh build directory `C:\bfin` (created empty this
   round; no incremental reuse of any earlier build tree). Configure + ninja
   invocation captured verbatim in `scripts/build_bfin.sh`,
   `raw/build/configure_bfin.log`, `raw/build/build_bfin.log`.
3. **Binary SHA256** (recorded at build completion, `BINARY_SHA256.txt`):
   - `MIOpen.dll` = `c739cb0e143162694c331ef8137e686418d003769ed7ad25c96945fe63a6fb42`
   - `test_hiprtc_selfcontained.exe` = `5f0c3f131ab21c53e729d65f1f8272291b9cdf23ce54374e82fba17c1e61e33e`
   - `test_kthvalue.exe` = `aecb6ce4bc2d53d9e1e6100de009eb6823c652fca9e425335a17d426b76c0d7f`
4. **Binary → runtime (build-tree legs B/E)**: each run's MIOpen log carries
   - `GetLibPath: "C:\\bfin\\bin"` — the process resolved its load path to the
     freshly built binaries (exe-dir-first DLL resolution; the wheel copy was
     never on these PATHs ahead of `C:\bfin\bin`), and
   - the MIOpen user-kernel-cache directory label
     **`3.6.2.f0f330c4`** — MIOpen derives this label from the git state of
     the source tree at build time. A dirty or differently-committed tree
     yields a different label (e.g. the pre-squash R2 logs show
     `3.6.2.e4b9174a-dirty`). The label appearing as exactly
     `3.6.2.f0f330c4` proves the running binary was built from a clean tree
     at the final PR HEAD.
5. **Binary → runtime (wheel-swap legs D/F)**: the wheel's
   `_rocm_sdk_libraries/bin/MIOpen.dll` (pristine SHA256 `74b4ee03…`) was
   replaced by the `C:\bfin\bin\MIOpen.dll` copy (SHA256 verified equal to
   `c739cb0e…` while swapped in), the test process printed its actually
   loaded module path via `GetModuleFileNameA` in-process
   (`…site-packages\_rocm_sdk_libraries\bin\MIOpen.dll`), and the wheel DLL
   was restored and hash-verified to `74b4ee03…` afterwards. For the D-v2
   run the full swap transcript is archived
   (`raw/batchnorm/swap_transcript_v2.log`: `74b4ee03…` → `c739cb0e…` →
   `74b4ee03…`); the D-run-1/F swap-window hashes were printed to the
   driver console (not archived) — compensated by the archived v2
   transcript, the in-process module-path lines in all D/F logs, the
   `__FILE__`-embedded `C:/w56/…` diagnostics in the F log (proving the
   loaded DLL was built from the pinned worktree), the backup-file hash,
   and the current pristine wheel hash (independently re-verified by the
   Gate A audit).

## Why a fresh pinned rerun was required (honest disclosure)

The previous round (R2, 2026-10-14/15) validated a *pre-squash working tree*:
its logs embed cache label `3.6.2.e4b9174a-dirty`, and the test file used
there had **198 lines**, while the final committed
`projects/miopen/test/gtest/hiprtc_selfcontained.cpp` at `f0f330c4` has
**204 lines** (the gtest assertion moved from line 141 to line 147 between
the R2 run and the commit). Per the evidence rules for this package,
historical logs therefore classify as `INSUFFICIENT_PROVENANCE` w.r.t. the
final HEAD and were **not** converted into final-HEAD evidence. All five
legs in this package were re-executed against the pinned `f0f330c4` tree;
the R2 logs remain archived locally only.

## Integrity notes

- All SHA256 values above were computed with `sha256sum` on the file bytes as
  present on disk. No git-blob-SHA1 is presented as a SHA256 identity.
- The upstream PR branch was not modified, rebased, or force-pushed during
  this evidence round (read-only API queries + local worktrees only).
