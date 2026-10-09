# CI PORTABILITY AMENDMENT — R1 → R2 (test registration block only)

Source of requirements: Linux Phase 5.2.1 findings
(linux-w7900/phase5.2.1/findings/{CI_AMENDMENT_PROPOSAL,
CTEST_PORTABILITY_ANALYSIS}.md, evidence C2/C3, PR #7 at 73e51c4) +
user-directed defect F-C2-4 discovered during R2 revalidation.
Implementation: `projects/miopen/test/CMakeLists.txt`, inside the
`if(MIOPEN_USE_HIPRTC)` block patch 0003 adds — nothing else changed
(R1→R2 diff: 1 file, +91/−19; every production source byte identical).

## Defect → fix map

| Defect | Mechanism | Fix in R2 |
|---|---|---|
| F-C2-1 | Test probe returns exit 4 INCONCLUSIVE on hosts that cannot reproduce no-STL isolation; raw registration renders it Failed (ctest rc 8) — a correct patch goes RED on such CI legs | `SKIP_RETURN_CODE 4`: exit 4 → Skipped/Not-Run, ctest rc 0; skip visible in "tests did not run" list; never counted as kernel PASS |
| F-C2-2 | Plain-name `hiprtc` link (non-WIN32 arm) carries no usage requirements; Linux package exports ONLY namespaced `hiprtc::hiprtc` (INTERFACE_INCLUDE_DIRECTORIES + location); test deliberately links nothing else → compile/link failure | `if(TARGET hiprtc::hiprtc)` → namespaced target; plain name kept only as fallback; find_package(hiprtc) at parent :600 runs before the test dir, so the probe is meaningful |
| F-C2-3 | Upstream `MIOPEN_TEST_GDB` defaults On (test/CMakeLists:96); non-WIN32 branch registers a cmake -P wrapper: execute_process RESULT + `message(FATAL_ERROR "Test failed")` on any nonzero — exit codes never reach CTest, SKIP_RETURN_CODE can never match | Direct `add_test` (no wrapper); raw exit code IS the CTest verdict on every platform |
| (policy) | A bare direct add_test would bypass SKIP_TESTS / SKIP_ALL_EXCEPT_TESTS (MIOPEN_NO_GPU, INT8, BF16 allowlists) that add_test_command enforces | The helper's exact guard replicated (echo skipped + DISABLED On), wrapping BOTH arch branches; ENVIRONMENT MIOPEN_USER_DB_PATH preserved (helper's trailing parity) |
| F-C2-4 | Windows loader: hiprtc DLL in `<prefix>/bin`, import lib on link line in `<prefix>/lib` — bare ctest run cannot START the test (0xC0000135). Latent in R1 (evidence scripts pre-set PATH) | Runtime dir derived from imported-target location metadata (IMPORTED_LOCATION, else first existing INTERFACE_LINK_LIBRARIES entry; pkg-root `bin/` if it exists else lib dir); prepended to PATH in the test's ENVIRONMENT with the configure-time PATH escaped (`string(REPLACE ";" "\\;" …)`) so it stays ONE env entry |

## Verdict semantics (unchanged binary contract)

| Exit | Meaning | CTest rendering |
|---|---|---|
| 0 | PASS (probe proved isolation; real kernel compiled; non-empty code object) | Passed |
| 1 | FAIL (any verdict shortfall — including a broken patch on an isolating host) | Failed (rc 8) |
| 2 | setup error (bad args/mode/dir, unreadable source) | Failed (rc 8) |
| 4 | INCONCLUSIVE (host cannot reproduce no-STL; negative-control signature discrimination refuses) | **Skipped / Not Run** (rc 0) — new in R2 |

## Disclosure of remaining deltas vs add_test_command (reviewed, accepted)

- WORKING_DIRECTORY (`${KERNELS_BINARY_DIR}` on WIN32) dropped — the test's
  only file I/O is an argv-derived absolute kernel path; hiprtc compiles
  in memory (verified in source + by Linux C2 audit).
- The Linux gdb-core backtrace convenience does not apply to this test
  (direct registration) — crash still FAILS hard, only the wrapper's
  `gdb ... core` traceback is absent.
- ENVIRONMENT on the disabled (echo skipped) branch is inert — a DISABLED
  test never executes.
- Configure-time PATH bake-in: canonical pre-3.22 CMake idiom
  (`ENVIRONMENT "PATH=<dir>\;$ENV{PATH}"` with escaped separators);
  `ENVIRONMENT_MODIFICATION` would require CMake 3.22, above MIOpen's
  declared 3.15 floor. Degradation is safe: if the runtime dir cannot be
  derived (no imported target / no location metadata), behavior falls
  back to exactly R1's ambient-PATH reliance — never worse.

## Windows proof points (evidence/phase5_1_r2/ci/)

- ci_integration.json + logs: configure/build/discover/run all PASS on
  f18c4de9; generated CTestTestfile carries ENVIRONMENT (MIOPEN_USER_DB_PATH
  + PATH prepend) + SKIP_RETURN_CODE "4"; genuine no-STL PASS (Passed,
  100%, not skipped).
- fc24_loader_failure_repro.json: clean-env failure 0xC0000135 (pre-fix).
- fc24_fix_ctest_clean_env.json: same clean env → Passed, rc 0 (post-fix).
- fc24_dll_load_provenance.json: in-process module snapshot → loaded
  `_rocm_sdk_core/bin/hiprtc0714.dll` `c6159dd1…` (exact stack match).
- ci_matrix_phase5_1.json: 13/13 adversarial cells (incl. CPATH STL-reach
  → exit 4; unpatched-tree positive → exit 1 with exact signature).
- exit_code_fixture.json: 0→PASS rc0, 1→FAIL rc8, 2→FAIL rc8, 4→SKIP rc0.
- ci_configure_bf16.log + generated CTestTestfile: restricted-leg parity.
