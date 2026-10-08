# P5-17 Post-Amendment Delta Re-Check

- Reviewer: CI/test engineer (focused delta re-check)
- Date: 2026-10-08
- Candidate worktree: `C:\Users\rocm\Desktop\YOLO_AMD\rocm-libraries-phase5-candidate`, branch `prepare/miopen-hiprtc-phase5`
- Scope: verify the post-review amendment (old tip `39319c4d` → new tip `29846fc4`) is exactly what was claimed and nothing else. NOT a full re-review of the series; the four P5-17 panel reviews cover the pre-amendment content.
- Binary under test: `C:\Users\rocm\Desktop\YOLO_AMD\phase5_build\ci_test\bin\test_hiprtc_selfcontained.exe` (mtime 2026-10-08 14:40, matches commit-3 author date; amendment-specific behaviors verified present below, so the binary demonstrably postdates the amendment)

## Verdict: PASS

All seven checks pass. One NIT (CMake comment lines go slightly beyond the literal claim wording; non-functional). No BLOCKER, MAJOR, or MINOR findings. No unintended delta.

## Per-check results

### 1. History shape and commit-1 identity — PASS

`git log --oneline 7c58661..HEAD` yields exactly 3 commits:

```
29846fc4 MIOpen: add HIPRTC no-host-STL regression test
66f66944 MIOpen: make remaining RTC kernel std includes self-contained
135f775e MIOpen: keep RTC type traits self-contained when no host STL is reachable
```

Full SHAs and linear parent chain:

| commit | full SHA | parent |
|---|---|---|
| 1 | `135f775e855bc40185d0a39e13d0a1a97105c1b9` | `7c5866144ac4b879be442563e2b49fa1c142ea36` (base) |
| 2 | `66f66944f171628076785e5b89b4a1334d5a987d` | commit 1 |
| 3 | `29846fc4fb736800ff0ad91af95c7cc32f1373ad` (= HEAD) | commit 2 |

Old series was `135f775e` → `b1adc77a` → `39319c4d`. **Commit 1 carries the identical full SHA `135f775e855bc40185d0a39e13d0a1a97105c1b9` in both old and new history** (same content, same parent, same author/date). The non-regression proof for everything reviewed under commit 1 holds unchanged. Working tree clean.

### 2. Tree-level delta and CMake token inspection — PASS (with 1 NIT)

`git diff --stat 39319c4d..HEAD` touches ONLY the two claimed files:

```
projects/miopen/test/CMakeLists.txt           |  9 ++++++-
projects/miopen/test/hiprtc_selfcontained.cpp | 36 ++++++++++++++++++++++++++-
2 files changed, 43 insertions(+), 2 deletions(-)
```

`projects/miopen/test/CMakeLists.txt` contains exactly one hunk (@@ -503,7 +503,14 @@ inside `if(MIOPEN_USE_HIPRTC)`): the single line

```cmake
target_link_libraries(test_hiprtc_selfcontained PRIVATE hiprtc::hiprtc)
```

is replaced by the platform split

```cmake
if(WIN32)
    target_link_libraries(test_hiprtc_selfcontained PRIVATE hiprtc::hiprtc)
else()
    target_link_libraries(test_hiprtc_selfcontained PRIVATE hiprtc)
endif()
```

This mirrors `projects/miopen/src/CMakeLists.txt` lines 1092-1099 exactly (namespaced `hiprtc::hiprtc` under `if(WIN32)`, plain `hiprtc` in the `else()` arm) — resolves Reviewer B MAJOR M1. No other CMake edits; the pre-existing `if(WIN32) NOMINMAX` block below is untouched (context only).

- **NIT-1**: the hunk also adds a 3-line explanatory comment ("Mirror the platform split src/CMakeLists.txt uses..."). This goes slightly beyond the literal claim wording ("replacing the single line with the if/else split"), but is comment-only, accurate, and non-functional. No action required.

### 3. Test-source delta enumeration — PASS

`git diff 39319c4d..HEAD -- projects/miopen/test/hiprtc_selfcontained.cpp` contains exactly 3 hunks, all within the claimed categories:

- **Hunk 1** (@@ -311,9 +311,12 @@, `stdlib_is_reachable`): (a) 2 comment lines added ("The probe covers all four standard-library headers the patch gates...") and (b) the probe source string extended from `#if __has_include(<type_traits>)` to `#if __has_include(<type_traits>) || __has_include(<utility>) || __has_include(<limits>) || __has_include(<initializer_list>)`. The four headers exactly match the patch scope (commit 1: `<type_traits>`, `<utility>`; commit 2: `<limits>`, `<initializer_list>`). Everything else in the probe (`#error STL_PROBE_REACHABLE`, `extern "C" __global__ void probe() {}`) is unchanged.
- **Hunk 2** (@@ -352,15 +355,29 @@ + @@ -372,7 +389,12 @@, arg loop in `main`): (c) duplicate-arg booleans `seen_mode`/`seen_arch`/`seen_hip_flat`/`seen_isolate` declared and set; each duplicate occurrence returns `usage(argv[0])` before assignment; one inline comment ("duplicate would silently downgrade a run"). Applies to all four string/flag options symmetrically; `--hip-flat=` keeps its existing `std::stoull` try/catch body untouched.
- **Hunk 3** (@@ -419,6 +441,18 @@, after `read_file`): (d) identity-marker SETUP check — refuses the kernels dir unless `kernel_src` contains both `"MIOpenBatchNormFwdTrainSpatial"` and `"__global__"`, printing the "lacks the real BN spatial kernel identity markers; refusing to test a substituted source" message and returning `kExitSetup`. 3 explanatory comment lines accompany it.

Explicit non-change confirmation:

- Exit-code constants identical old vs new (`kExitPass=0`, `kExitFail=1`, `kExitSetup=2`, `kExitInconclusive=4`; `usage()` returns `kExitSetup` in both).
- No diff hunk touches `kernel_options()` (compile options), the signatures list, `stdlib_is_reachable`'s verdict interpretation, the positive/negative/with-stl/ordinary verdict arms, or the negative-mode expectations. The `#error STL_PROBE_REACHABLE` string and probe interpretation are unchanged — the probe extension only widens what counts as "reachable", which is the claimed hardening (F1/F3 territory), not a semantics change.

### 4. Commit-2 message and tree — PASS

`git log -1 --format=%B 66f66944`:

- tensor_view paragraph now reads: "Unlike the type_traits/utility probes of the first commit, this probe is deliberately **not HIP-version-gated and carries no partial-STL cross-probe**: both headers it selects between define the same single class, so a mixed environment cannot produce conflicting definitions." — Reviewer A MINOR-3 addressed.
- `DCO: PENDING HUMAN CONFIRMATION - provisional local commit, not for upstream submission; replace this line with a real Signed-off-by per DCO before submitting.` — intact. No actual `Signed-off-by:` trailer exists (the only grep hit is the DCO instruction line itself).

`git show --stat 66f66944` contains exactly the claimed four files:

```
projects/miopen/src/CMakeLists.txt                 |  1 +
.../miopen_freestanding_initializer_list.hpp       | 60 ++++++++++++++++++++++
projects/miopen/src/kernels/radix.hpp              | 11 +++-
projects/miopen/src/kernels/tensor_view.hpp        |  7 +++
```

The 1-line CMake change is the registration `kernels/miopen_freestanding_initializer_list.hpp` added to the freestanding-headers list (lines ~511-514), i.e., the registration line is in the correct commit. Furthermore `git rev-parse 66f66944^{tree}` == `git rev-parse b1adc77a^{tree}` == `f0d55fb6a065a9d4a88421c987f1641be5c0a242`: **commit 2 is a message-only change; its tree is byte-identical to the pre-amendment commit 2** (the registration line was already correctly placed pre-amendment; only the message improved).

### 5. Patch file identity — PASS

SHA256 of exact file bytes in `patches\phase5\canonical\`:

| file | computed SHA256 | expected (PATCH_IDENTITY.json) | match |
|---|---|---|---|
| 0001-...no-h.patch | `76fd6623958fb58fc71a9fabbf662bc28a22cfd19aeacba76ca9eee841abc586` | `76fd6623...` | YES |
| 0002-...self-c.patch | `d37376c9318c79f750b456ff6491ed1e6978d0eafa45a49a34fc66cf85f7a9ea` | `d37376c9...` | YES |
| 0003-...test.patch | `593061053e113c5005040d6d9b1dee39c4d0d7cb2d0c27626749815ed6877821` | `59306105...` | YES |
| concatenated series (sha256_file_concat_v1, LF, no separator, in order) | `5ad951c716fbf986e627a94f65db679f4f49519d672912cb2e407bf3b714391d` | `5ad951c7...` | YES |

PATCH_IDENTITY.json `new_commit_shas` also lists `135f775e.../66f66944.../29846fc4...`, matching the worktree.

Fresh `git format-patch 7c58661..HEAD` regenerated to a temp dir: **all three files byte-identical (`cmp`) to the canonical copies**. The canonical patches are exactly the candidate's series.

### 6. Behavioral spot-checks — PASS (4/4)

All runs with PATH prefixed by `_rocm_sdk_core\bin`; gfx1151.

| # | scenario | command shape | observed | expected | result |
|---|---|---|---|---|---|
| a | duplicate `--mode` | `--mode=positive --mode=negative <pristine-kernels>` | usage printed, `EXIT=2` | exit 2 | PASS |
| b | substituted kernels dir | temp dir = pristine `*.hpp` copies + trivial `extern "C" __global__ void trivial_kernel() {}` written to `MIOpenBatchNormFwdTrainSpatial.cpp`, `--mode=positive` | `SETUP ERROR: MIOpenBatchNormFwdTrainSpatial.cpp lacks the real BN spatial kernel identity markers; refusing to test a substituted source`, `EXIT=2` | exit 2 + identity-marker message | PASS |
| c1 | positive, pristine (unpatched) kernels | `--mode=positive <pristine-kernels>` | `fatal error: 'type_traits' file not found` (miopen_type_traits.hpp:151), `FAIL: positive compile did not produce a code object`, `EXIT=1` | exit 1 (unpatched expected-failure) | PASS |
| c2 | positive, candidate (patched) kernels | `--mode=positive <candidate-kernels>` | `PASS: kernel compiled without host STL (5784-byte code object)`, `EXIT=0` (warnings only) | exit 0 | PASS |

Note: checks (a) and (b) exercise behaviors that exist only in the amended source, so the rebuilt binary is proven to incorporate the amendment (not a stale pre-amendment build).

### 7. src/include non-regression — PASS

`git diff 39319c4d..HEAD -- projects/miopen/src projects/miopen/include` → **empty** (0 lines). The DLL-validity premise holds: the src tree at the new tip is byte-identical to the src tree at the old tip (and both differ from base only by the 8 audited files of commits 1-2, per `git diff 7c58661..HEAD --stat -- projects/miopen/src`, unchanged by the amendment).

## Findings summary

- BLOCKER: none
- MAJOR: none
- MINOR: none
- NIT-1: CMakeLists hunk includes a 3-line comment beyond the literal claim wording ("replace the single line with the if/else split"). Comment-only, accurate, non-functional. No action required.

## Unintended delta found

None. Every hunk in the amendment maps to a claimed change; no file outside the two claimed test files differs between `39319c4d` and `29846fc4`; commit 1 and commit 2 trees are bit-identical to their pre-amendment counterparts; canonical patch bytes regenerate exactly from the candidate history.
