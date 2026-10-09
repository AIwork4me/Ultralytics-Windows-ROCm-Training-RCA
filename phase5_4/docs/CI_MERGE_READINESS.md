# REGRESSION TEST CI QUALITY / MERGE READINESS — Gate P54-05

Mission: `WINDOWS-P54-MIOPEN-UPSTREAM-MERGE-READINESS`
Perspective: upstream CMake/CTest maintainer. Object: R2 patch 3's test integration (`projects/miopen/test/CMakeLists.txt` registration block + `test/hiprtc_selfcontained.cpp`), replayed byte-identically onto develop `681bc9ed` (replay commits `0af085f1/69e7ff07/cab3f08a`).
Fresh empirical evidence in this gate: configure + build + ctest on the replay tree (`phase5_4_build/ci_test`), the 13-cell adversarial matrix, a bare-environment ctest, and a BF16 restricted-leg configure (`phase5_4_build/ci_test_bf16`). Linux evidence: frozen W7900 Phase-5.3 L07 (immutable links).

## 1. Checklist verification

| Requirement | Status | Evidence |
|---|---|---|
| `hiprtc::hiprtc` imported target compatibility | ✅ | `if(TARGET hiprtc::hiprtc)` branch taken on Windows; ninja link line resolves `…/_rocm_sdk_core/lib/hiprtc.lib` from imported-target metadata (`build.ninja` LINK_LIBRARIES). |
| Plain `hiprtc` fallback correctness | ✅ | Fallback exists for packages exporting no namespaced target; exercised on stock Linux (Phase-5.3 L05/L07: target built with no manual workarounds). Deliberately links nothing else (rationale comment in-tree). |
| Direct `add_test` registration | ✅ | Registered by hand, not via `add_test_command`; `miopen-tests`/`miopen-check` dependencies added; excluded from the glob via `EXCLUDE_TESTS`. |
| `SKIP_RETURN_CODE 4` | ✅ | Set via `set_tests_properties`; exit-code fixture today: 0→Passed, 1→FAIL (bad-arch cell), 2→FAIL (missing-dir/bad-mode cells), 4→SKIP (CPATH-INCONCLUSIVE cell). |
| Skip-list/allowlist parity | ✅ **re-proven today** | BF16 leg (`-DMIOPEN_TEST_BFLOAT16=ON`) → `ctest -N` shows `Test #10: test_hiprtc_selfcontained (Disabled)` — identical treatment to `add_test_command` tests under `SKIP_ALL_EXCEPT_TESTS` (`bf16_leg_ctest_n.log`). |
| `MIOPEN_TEST_GDB` behavior | ✅ by design | Direct registration avoids the GDB wrapper (default On for non-WIN32) that folds every nonzero exit into generic failure — the skip contract would be unobservable otherwise. In-tree comment documents this. |
| Windows test-specific DLL PATH | ✅ **re-proven today** | Bare-env ctest (PATH=System32 only, no ambient ROCm): `1/1 … Passed, 100% tests passed` (`ci_ctest_bare_env.log`) — the configure-time WIN32 PATH prepend from imported-target metadata works standalone (F-C2-4 semantics intact on replay). |
| Correct test executable working directory | ✅ | Kernel dir passed as absolute argument (`${CMAKE_CURRENT_SOURCE_DIR}/../src/kernels`), not CWD-dependent. |
| Correct kernel include directory | ✅ | Adversarial cell "wrong include dir (src/, not kernels/)" → exit 2 setup-failure (no false pass). |
| GPU target propagation | ✅ | Arch chain: `MIOPEN_TEST_HIPRTC_ARCH` cache → `GPU_TARGETS[0]` → `CMAKE_HIP_ARCHITECTURES[0]` (feature-suffix stripped) → gfx1151 built-in default; today's run used the configured gfx1151. |
| Test selection on non-Windows hosts | ✅ | Same SKIP_TESTS/SKIP_ALL_EXCEPT_TESTS policy; Linux L07: ordinary/with-STL PASS, no-STL SKIP. |
| Exit codes 1/2 remain failures | ✅ | Matrix cells: bad-arch rc=1 FAIL, missing-dir rc=2 FAIL, bad-mode rc=2 FAIL. |
| Linux INCONCLUSIVE visible as SKIPPED | ✅ | L07 fixture evidence (probe → exit 4 → CTest "Skipped / Not Run", rc 0); Windows CPATH cell shows the same mapping locally. |
| Genuine Windows no-STL success mandatory | ✅ | Default ctest run = **Passed** (0.61s), not Skipped; matrix `positive/patched` rc=0. |

## 2. Maintainability assessment — would a maintainer prefer a shared helper?

The registration duplicates ~4 lines of skip-policy from `add_test_command` (SKIP_TESTS / SKIP_ALL_EXCEPT_TESTS). Alternatives:

- **A. Keep as-is (chosen)**: duplication is small, locally reasoned, and avoids touching a helper used by every other MIOpen test. The alternative `add_test_command(... RAW)` option would modify shared CI infrastructure inside a bugfix PR — larger review surface, higher regression risk, and impossible to validate on stock Linux CI from this contributor's position.
- **B. Refactor `add_test_command` upstream** to support raw exit codes + pass-through ENVIRONMENT: worth an upstream discussion, but as a **separate follow-up PR** by whoever owns the test framework contract. This PR documents the trade-off instead.

**Recommendation: no source change in this contribution.** The block is well-commented, each non-obvious choice states its constraint, and every semantic is fixture-proven on two platforms.

## 3. Residual notes (documentation-level)

1. The `echo skipped` placeholder in the disabled-leg registration is a Unix command; on Windows shells ctest warns it cannot pre-resolve `echo` (seen in today's BF16 `-N` output). Harmless — the test is `DISABLED` and never launched — but worth one PR sentence (Linux Reviewer-A m2). Byte-parity with the existing `add_test_command` helper idiom (Reviewer B nit 1).
2. `clang_tidy_check` is applied to the new test target (convention parity).
3. `MIOPEN_USER_DB_PATH` is set to the build dir for the test env — hermetic, no user-state writes.
4. CMake minimum / policy surface: uses only long-stable commands (`add_test`, `set_tests_properties`, `get_target_property`, `string(FIND/SUBSTRING/REPLACE)`, `list(APPEND/GET)`) — no version-sensitive APIs observed.
5. **Ambient `CPATH` on CI images (Reviewer B MINOR 2):** the test's `ENVIRONMENT` property does not clear `CPATH`; a runner image exporting it (conda/LLVM toolchain images) makes the host STL reachable → the probe fires → the run reports **Skipped, exit 0, suite stays green while losing this regression's coverage**. Capability-aware by design (never a false verdict — the "did not run" list is visible), but the no-STL CI leg must be provisioned without ambient `CPATH`, ideally with a pipeline assertion that this test was not skipped on that leg. Captured as a PR sentence.
6. The configure-time PATH baking pins the run-time `PATH` to `<hiprtc dir> + configure-time $ENV{PATH}` — the only CTest-native mechanism (CTest cannot evaluate env at run time); configure/run host divergence fails loudly (DLL not found). Single-host contract stated for multi-machine CI (Reviewer B MINOR 3).
7. The two ad-hoc checks behind `ci_ctest_bare_env.log` / `bf16_leg_ctest_n.log` are now reproducible via `scripts/bare_env_and_restricted_leg_checks.py` (Reviewer B MINOR 1; interactive originals were run during the gate — replay logs land beside the originals with a `.replay.log` suffix).

## 4. Verdict

**PASS** — the regression test is CI-merge-ready: portable linkage, honest skip semantics, fixture-proven exit-code contract, restricted-leg parity, standalone Windows DLL resolution, and no false-PASS loopholes found by the 13-cell adversarial matrix. Recommended follow-up (out of scope): upstream discussion of a raw-exit-code option for `add_test_command`.

*Independent CMake/CTest review: performed as Reviewer B of the Gate P54-11 panel.*
