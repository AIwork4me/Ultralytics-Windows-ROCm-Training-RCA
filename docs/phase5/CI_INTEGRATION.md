# CI Integration (Gates P5-06 + P5-07 + P5-08)

Date: 2026-10-08. Candidate: `prepare/miopen-hiprtc-phase5` @
`39319c4d2f51998529dc0f2144841ba4cbe82ff3` (commit 3 =
"MIOpen: add HIPRTC no-host-STL regression test").

## What was integrated

The Phase-4 standalone regression test
(`patches/phase4/ci_test_proposal/hiprtc_selfcontained.cpp`, 6/6 matrix
validated + two adversarial hardening rounds) is now a first-class
in-tree MIOpen CTest:

- `projects/miopen/test/hiprtc_selfcontained.cpp` — the validated test
  source, clang-format-18.1.4-clean for the in-tree style. Byte-delta vs
  the Phase-4 artifact (beyond formatting):
  1. `get_log()` restructured to a single named-object return — MIOpen's
     in-tree `-Werror -Wnrvo` rejected the mixed `return {};`/`return log;`
     form. Semantics unchanged (verified by the rerun matrix below).
  2. No other logic changes (token-stream check during integration; the
     P5-08 matrix re-validated all verdicts with the final source).
- `projects/miopen/test/CMakeLists.txt` — registration:
  - excluded from the `add_test_executable` glob (it must NOT link
    `MIOpen_with_plugins`; it drives hiprtc exactly like the runtime
    compile path, without MIOpen in the process);
  - gated on `MIOPEN_USE_HIPRTC` (the actual upstream option; imported
    target `hiprtc::hiprtc` — the same target `src/CMakeLists.txt` links
    the implementation against);
  - `clang_tidy_check` + WIN32 `NOMINMAX` + aggregate wiring into
    `miopen-tests`/`miopen-check`, mirroring `add_test_executable`;
  - architecture selected at configure time: `MIOPEN_TEST_HIPRTC_ARCH`
    cache override → first `GPU_TARGETS` entry (feature suffix stripped)
    → first `CMAKE_HIP_ARCHITECTURES` entry → test default gfx1151;
    forwarded as `--arch=` (no generator expressions);
  - registered through the repo's own `add_test_command` (honors skip
    lists, WIN32 `$<TARGET_FILE>` form, `MIOPEN_USER_DB_PATH`).

The negative control stays OUT of the default suite by design: a normal
patched checkout runs the positive expectation only; `--mode=negative`
(and ordinary/with-stl) remain available to A/B harnesses.

## Verification performed (all commands logged under evidence/phase5/ci/)

| Step | Result | Log |
|---|---|---|
| CMake configure (`BUILD_TESTING=ON`, Ninja, validated Phase-3/4 shim toolchain, fresh dir `phase5_build/ci_test`) | PASS exit 0 | ci_configure.log |
| Target build (`cmake --build --target test_hiprtc_selfcontained`) | PASS exit 0 | ci_build_target.log |
| CTest discovery (`ctest -N -R test_hiprtc_selfcontained`) | PASS exit 0 — registered as Test #10 with `<kernels-dir> --arch=gfx1151` | ci_ctest_discovery.log |
| CTest execution (`ctest -R ^test_hiprtc_selfcontained$ --output-on-failure`) | PASS exit 0 — Passed 0.68 s | ci_ctest_run.log |

Registered command (from `test/CTestTestfile.cmake`):

```text
add_test(test_hiprtc_selfcontained ".../bin/test_hiprtc_selfcontained.exe"
         ".../projects/miopen/test/../src/kernels" "--arch=gfx1151")
```

Environment deltas vs a stock Linux CI host (all recorded in
`ci_integration.json`):
- GTest provided in CONFIG mode from `phase5_deps/gtest_prefix`
  (googletest 1.14.0 built with the same clang toolchain) because the
  machine has no distro `libgtest-dev`; upstream's `test/gtest` needs
  `GTest::gmock`, which MODULE-mode FindGTest cannot supply.
- `MIOPEN_USE_COMPOSABLEKERNEL=OFF` for this configure: without an
  installed CK package the CK-header gtests cannot link; upstream
  documents this configure as clean (the flag gates only per-arch CK
  plugins and CK-header gtests). Does not affect the test under test or
  the DLL build config used in P5-09.

## P5-08 — adversarial A/B matrix (13/13 PASS)

Binary under test: the CTest-built
`phase5_build/ci_test/bin/test_hiprtc_selfcontained.exe`
(SHA256 in `ci_matrix_phase5.json`); unpatched tree = frozen develop
`7c58661` pristine worktree; patched tree = candidate `39319c4d`.

| Cell | Exit | Verdict |
|---|---|---|
| ordinary/unpatched | 0 | PASS |
| ordinary/patched | 0 | PASS |
| positive(no-STL)/unpatched | 1 (expected failure) | PASS |
| positive(no-STL)/patched | 0 | PASS |
| negative(no-STL)/unpatched | 0 (exact `fatal error: 'type_traits' file not found` signature, sole error) | PASS |
| negative(no-STL)/patched | 1 (rejects the negative expectation) | PASS |
| with-stl/unpatched | 0 | PASS |
| with-stl/patched | 0 | PASS |
| adv: missing kernels dir | 2 (SETUP) | PASS |
| adv: wrong include dir | 2 (SETUP) | PASS |
| adv: bad arch `gfx9999` | 1 (FAIL, no crash) | PASS |
| adv: bad mode | 2 (usage) | PASS |
| adv: STL injected via CPATH | 4 (INCONCLUSIVE — reachability probe held) | PASS |

Overall: **PASS** (`evidence/phase5/ci/ci_matrix_phase5.json`; full
compiler logs, code-object sizes, test/binary/HIPRTC-DLL SHA256, tree
SHAs recorded per cell).

Known environmental caveat, disclosed: an uncommitted fix was
transiently reverted by the build script's worktree-restore step during
one iteration; the final series was re-validated with the fix committed
first (`source_git_head` = `39319c4d` matches the validated bytes).

---

## Post-panel amendment (after P5-17 Reviewer B) — FINAL state

Reviewer B's MAJOR M1 and the P508 attacker's hardening conditions were
resolved in the final series (`29846fc4`):

1. **hiprtc linkage platform split** (M1): the registration now mirrors
   `src/CMakeLists.txt:1093-1099` exactly — `hiprtc::hiprtc` under
   WIN32, plain `hiprtc` elsewhere. On stock Linux the hiprtc package
   exports no namespaced `hiprtc::hiprtc` target (only
   `hiprtc-builtins`), so the previous unconditional namespaced link
   would have been a hard configure error (CMP0028) on the first
   stock-Linux HIPRTC test leg. Clarifies the earlier wording in this
   document that implied src uses `hiprtc::hiprtc` unconditionally.
2. **Kernel identity markers** (P508 F1): substituted/truncated kernel
   sources are refused (SETUP exit 2); verified with a trivial-kernel
   substitution that previously returned exit 0.
3. **Duplicate-argument rejection** (P508 F3): repeated
   `--mode/--arch/--hip-flat/--isolate` now produce usage errors
   (verified exit 2), closing the last-wins downgrade vector.
4. **Four-header probe** (P508 F4): the STL-unreachability probe now
   tests `__has_include` for `<type_traits>`, `<utility>`, `<limits>`
   and `<initializer_list>`.
5. Timing note correction (B N1): the CTest run logged 0.16–0.68 s
   depending on cache state; both runs are in the logs.

Revalidation at `29846fc4` (`ci_integration.json` source_git_head):
configure/build/discovery/run **4/4 PASS**; matrix **13/13 PASS**
(`ci_matrix_phase5.json`). The src/ tree is byte-identical to the
commit the DLL was built from (test-only delta), so the built
MIOpen.dll remains the validated artifact.

Remaining known non-blocking items (documented, not fixed here):
INT8/BFLOAT16/NO_GPU CI legs set `SKIP_ALL_EXCEPT_TESTS` without this
name, so those legs skip it ("Not Run", coverage loss — an upstream CI
wiring decision); Windows runtime relies on the harness PATH for the
hiprtc DLL (fails closed: ctest reports Failed on missing DLL).
