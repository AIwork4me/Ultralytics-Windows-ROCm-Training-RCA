# Gate R21 — Formal Defect Reproduction (F-C2-1 / F-C2-2 / F-C2-3)

Windows-side formal review of the Linux Phase-5.2.1 findings before amending
the frozen P5.1-CANDIDATE-R1 patch 0003. Every mechanism claim below was
re-inspected against the ACTUAL sources on this machine (not taken from the
Linux documents):

- Upstream helper `add_test_command`: `projects/miopen/test/CMakeLists.txt`
  lines 326–350 at frozen base 7c586614 (R1 worktree).
- Skip-list population: same file lines 283–311 (MIOPEN_TEST_INT8 /
  MIOPEN_TEST_BFLOAT16 / MIOPEN_NO_GPU allowlists, SKIP_TESTS appends).
- BUILD_TESTING gate: `projects/miopen/CMakeLists.txt:966–969`
  `if(BUILD_TESTING) add_subdirectory(test)`.
- KERNELS_BINARY_DIR: `projects/miopen/CMakeLists.txt:626/628` (build-tree
  bindir / database dir where kernel DBs are extracted).
- Windows hiprtc CMake package: local shim used by every validated Windows
  build (`phase3_deps/cmake_shims/hiprtc/lib/cmake/hiprtc/hiprtc-config.cmake`)
  does `add_library(hiprtc::hiprtc INTERFACE IMPORTED)` with
  `INTERFACE_INCLUDE_DIRECTORIES` → `_rocm_sdk_core/include`.
- Linux evidence: `linux-w7900/phase5.2.1/findings/{CI_AMENDMENT_PROPOSAL,
  CTEST_PORTABILITY_ANALYSIS}.md`, `evidence/{C2_ctest_portability,
  C3_mechanism_validation}.json`, `reviews/C3_maintainer_review.md`
  (origin/main 73e51c4, PR #7).

## Defect table

| DEFECT | ROOT CAUSE | LINUX EVIDENCE | WINDOWS IMPACT | MINIMAL CHANGE | REGRESSION RISK |
|---|---|---|---|---|---|
| F-C2-1: honest INCONCLUSIVE (exit 4) renders as CI failure | Test's STL-unreachability probe returns exit 4 on hosts that cannot reproduce no-STL; R1 registration forwards the raw exit code to CTest with no skip policy | ROCm 7.14.1: libhiprtc-builtins embeds type_traits/limits/initializer_list, reachable under every isolation flag combo (B06/C2.5); direct run: positive=4, negative=4, with-stl=0, ordinary=0 (C2.4); via CTest: `***Failed`, 0% passed, rc 8 (C2_ctest_run.log) | None today: Windows CAN isolate (probe passes, verdict 0/1). But the P5-08 CPATH-injection adversarial cell produces exit 4 on Windows too — without a skip policy that cell renders Failed under CTest | `SKIP_RETURN_CODE 4` on the test property | Low: exit 0/1/2 semantics untouched; a genuine regression (1) still fails hard; only the already-defined INCONCLUSIVE code becomes Not-Run |
| F-C2-2: test target does not BUILD on Linux as registered | R1 block mirrors src/CMakeLists.txt's WIN32 split: plain `hiprtc` on non-WIN32. Linux hiprtc package exports ONLY `hiprtc::hiprtc` (INTERFACE_INCLUDE_DIRECTORIES + IMPORTED_LOCATION); plain name carries no usage requirements and the test deliberately links nothing else | Compile fails `'hip/hiprtc.h' file not found`; with include dir supplied, link fails `unable to find library -lhiprtc` (C2.3). Impl target survives only because it also links hip::host/hip::device | None: Windows wheel-shim exports `hiprtc::hiprtc`; R1 already links the namespaced target on WIN32 (verified in shim config: `add_library(hiprtc::hiprtc INTERFACE IMPORTED)`) | Replace platform split with `if(TARGET hiprtc::hiprtc) … else() … endif()` | Low: on Windows the condition is TRUE → same namespaced target as R1 (no-op); plain-name arm retained only as fallback for packages lacking the namespaced target |
| F-C2-3: add_test_command's Linux default destroys the exit code | Upstream sets `MIOPEN_TEST_GDB On` (test/CMakeLists.txt:96); non-WIN32 GDB branch registers `cmake -P` wrapper: `execute_process(... RESULT_VARIABLE RESULT)` + `if(NOT RESULT EQUAL 0) message(FATAL_ERROR "Test failed")` — every nonzero exit (incl. 4) collapses to generic failure, so SKIP_RETURN_CODE can never match | Mechanism matrix (C3): helper registration → `***Failed` rc 8; direct add_test without property → `***Failed` rc 8; direct add_test + SKIP_RETURN_CODE 4 → `***Skipped`, 100% passed, rc 0 | None: WIN32 branch of helper registers the raw `$<TARGET_FILE:...>` — Windows CTest already sees real exit codes (Phase-5 CI PASS evidence) | Register via direct `add_test()` (bypass wrapper) + set SKIP_RETURN_CODE 4; keep helper's ENVIRONMENT parity (`MIOPEN_USER_DB_PATH=${CMAKE_CURRENT_BINARY_DIR}`) | Medium-managed: direct add_test bypasses the helper's skip-list/allowlist guard (DISABLED path) and the WIN32 WORKING_DIRECTORY — see disclosed deltas below; R2 adds the helper's exact list guard around the direct add_test to restore policy parity |

## Verified helper semantics (upstream test/CMakeLists.txt:326–350)

```cmake
function(add_test_command NAME EXE)
    if( (NOT (NAME IN_LIST SKIP_ALL_EXCEPT_TESTS) AND SKIP_ALL_EXCEPT_TESTS)
        OR (NAME IN_LIST SKIP_TESTS)
    )
        add_test(NAME ${NAME} COMMAND echo skipped)
        set_tests_properties(${NAME} PROPERTIES DISABLED On)
    elseif(WIN32)
        add_test(NAME ${NAME} COMMAND $<TARGET_FILE:${EXE}> ${ARGN}
                 WORKING_DIRECTORY "${KERNELS_BINARY_DIR}")
    else()
        if(MIOPEN_TEST_GDB)   # default On → cmake -P wrapper, exit code destroyed
            ...
        else()
            add_test(NAME ${NAME} COMMAND ${EXE} ${ARGN})
        endif()
    endif()
    set_tests_properties(${NAME} PROPERTIES
        ENVIRONMENT "MIOPEN_USER_DB_PATH=${CMAKE_CURRENT_BINARY_DIR}")
endfunction()
```

Policy-relevant populations (lines 283–311):
- `MIOPEN_TEST_INT8` / `MIOPEN_TEST_BFLOAT16` → `SKIP_ALL_EXCEPT_TESTS`
  lists that do NOT include test_hiprtc_selfcontained.
- `MIOPEN_NO_GPU` → `set(SKIP_ALL_EXCEPT_TESTS test_sqlite_perfdb)` — with
  the helper, our compile-only test is DISABLED on no-GPU legs today.
- `SKIP_TESTS` currently never lists test_hiprtc_selfcontained.

## Design decision for R2 (beyond the bare Linux proposal)

The Linux proposal's Hunk 2 registered the direct `add_test` WITHOUT the
helper's skip-list guard, disclosing the bypass as an accepted delta and
noting "if maintainers prefer parity, wrap the direct add_test in the same
list guard the helper uses" (C3 review finding #1). Mission Gate R22
CHANGE 4 explicitly directs: preserve the helper's skip-list/allowlist
semantics where practical, and test the MIOPEN_NO_GPU and restricted-list
configurations. Therefore R2 wraps the direct `add_test` in the helper's
EXACT guard condition (same `echo skipped` + `DISABLED On` disabled path),
keeping exit-code fidelity (direct add_test) AND selection policy parity.

Disclosed remaining deltas vs the helper (accepted, harmless):
- WORKING_DIRECTORY (WIN32 branch sets `${KERNELS_BINARY_DIR}`): dropped.
  The test's only file I/O reads `<kernels-dir>/<kernel>` from an
  argv-derived absolute path; hiprtc compiles in memory (Linux C2 +
  Phase-5 Windows evidence).
- The disabled path loses ENVIRONMENT/SKIP_RETURN_CODE parity — inert: a
  DISABLED test never executes (CTest "Not Run"); `echo skipped` exits 0
  regardless. ENVIRONMENT is still set for the active path exactly like
  the helper.
- `COMMAND test_hiprtc_selfcontained` (target name) instead of
  `$<TARGET_FILE:...>`: resolves to the built executable on all platforms;
  avoids generator-expression divergence between the guard's branches.

## Reproduction status

- F-C2-1/F-C2-3 Linux reproduction: NOT executable on this Windows host by
  design (mission: "DO NOT execute or claim Linux validation on Windows").
  Mechanism re-verified from upstream CMake source (above) + Linux logs.
- F-C2-3 Windows non-reproduction: consistent with helper source — WIN32
  branch passes raw exit codes (Phase-5/5.1 Windows CTest PASS evidence).
- F-C2-2 Windows non-reproduction: shim exports hiprtc::hiprtc (verified
  above); Linux package behavior per C2.3 hiprtc-targets.cmake inspection.

## SUBAGENT R21

See evidence/phase5_1_r2/subagent_reviews/R21_independent_audit.md.


## ADDENDUM (post-R26 interjection) — defect F-C2-4 discovered during revalidation

During R2 revalidation a FOURTH registration-portability defect surfaced on
Windows: the hiprtc runtime DLL lives in the package's <prefix>/bin while the
import library the link line carries is <prefix>/lib/hiprtc.lib, so a bare
ctest run without the package bin dir on PATH cannot START the test
(0xC0000135 STATUS_DLL_NOT_FOUND; repro recorded). Latent in R1 as well
(evidence scripts always prepended the dir). Fixed inside the same approved
block with a test-scoped ENVIRONMENT PATH prepend derived from the imported
target's location metadata. Full RCA: findings/phase5_1_r2/F_C2_4_DLL_LOADER_RCA.md.
