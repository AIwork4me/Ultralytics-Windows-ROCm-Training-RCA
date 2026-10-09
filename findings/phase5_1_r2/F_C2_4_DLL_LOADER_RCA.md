# F-C2-4 — Windows DLL loader RCA and fix (Gate interjection, R2 mission)

Reported symptom: `test_hiprtc_selfcontained.exe` cannot start —
"hiprtc0714.dll cannot be found". Classified (correctly) as a Windows
process-startup / DLL-resolution failure, NOT a HIPRTC kernel-compilation
regression. Discovered during R2 revalidation; fixed inside the approved
test registration block; all affected gates re-run; identities regenerated.

## 1. Inventory

- Active env: conda `yolo_amd` (Py3.13, torch 2.12.0+rocm7.14.0).
- ROCm stack: pip-wheel SDK `_rocm_sdk_core` (7.14.0); HIPRTC DLL
  `...\_rocm_sdk_core\bin\hiprtc0714.dll` SHA256
  `c6159dd12714eed42c1d851e49a425404c1a34ba27cd2a8e721b0fe3db4fd86e`
  (identical byte copy exists in the conda-base wheel; both hash equal).
  The DLL's only import is KERNEL32.dll (llvm-readobj) — no transitive
  ROCm DLLs needed.
- Test exe: `phase5_1_r2_build\ci_test\bin\test_hiprtc_selfcontained.exe`,
  RelWithDebInfo, direct imports (llvm-readobj --coff-imports):
  hiprtc0714.dll, MSVCP140.dll, KERNEL32.dll, VCRUNTIME140.dll, UCRT apiset
  DLLs — all system-resolvable EXCEPT hiprtc0714.dll.
- hiprtc0714.dll exists in NO default loader-search directory (System32,
  Windows, MSVC bin checked) — only inside the wheel's `bin\`.
- Imported CMake target: shim-exported `hiprtc::hiprtc` INTERFACE IMPORTED
  (include dir + full-path import lib `...\_rocm_sdk_core\lib\hiprtc.lib`).
  Import lib dir (`lib\`) ≠ DLL dir (`bin\`) — the link line carries no DLL
  location, so the loader depends entirely on PATH.

## 2. Reproduction (pre-fix)

Clean environment (PATH = System32;Windows;Wbem only — no `_rocm_sdk_core`,
no conda), R2 registration WITHOUT the fix:
- Direct exe: exit code 3221225781 = **0xC0000135 STATUS_DLL_NOT_FOUND**.
- `ctest -R '^test_hiprtc_selfcontained$'`: `Exit code 0xc0000135`,
  0% passed, ctest rc 8 (~47 s startup-failure timeout).
Evidence: `evidence/phase5_1_r2/ci/fc24_loader_failure_repro.json`.

Latent in R1 too: R1's registration (add_test_command WIN32 branch) never
touched PATH either; Phase-5/5.1 evidence runs masked the defect because the
evidence scripts always invoked ctest with `_rocm_sdk_core\bin` prepended to
PATH. Under R2's SKIP_RETURN_CODE 4 the loader failure (0xC0000135 ≠ 4)
renders as FAIL — honest, but the test is unrunnable on a bare Windows leg.

## 3. Root cause

Defect F-C2-4: the test registration exposes no hiprtc runtime-library
directory, and the hiprtc package layout places the DLL in `<prefix>\bin`
while the import library on the link line is `<prefix>\lib\hiprtc.lib`, so
a plain ctest run whose PATH lacks the package `bin\` cannot START the test
(STATUS_DLL_NOT_FOUND), regardless of the kernel fix's correctness.

## 4. Fix (inside the approved test registration block only)

Capability-aware, package-metadata-derived, test-scoped — no machine-wide
PATH change, no DLL copies, no security changes:

1. Derive the hiprtc runtime directory at configure time from the imported
   target's own location metadata: `IMPORTED_LOCATION` when the package sets
   it; else the first `INTERFACE_LINK_LIBRARIES` entry that is an existing
   file (the import library); then `<pkg root>/bin` if it exists, else the
   library's own directory (Linux .so layout).
2. Prepend that directory to PATH for THIS test only via the ENVIRONMENT
   test property (`PATH=<dir>\;$ENV{PATH}` documented CMake idiom),
   preserving `MIOPEN_USER_DB_PATH` parity and `SKIP_RETURN_CODE 4`.

Preserved: direct add_test; SKIP_TESTS/SKIP_ALL_EXCEPT_TESTS guard;
MIOPEN_USER_DB_PATH; arch selection; genuine Windows no-STL hard-PASS
(PATH does not influence include resolution — the isolated compile flags
are unchanged; the CPATH adversarial cell still yields exit 4).

Linux: the same derivation resolves to the package lib/bin directory and is
at most a harmless PATH entry; .so resolution is unchanged.

## 5. Post-fix validation (all on candidate HEAD 61410b68)

- Generated registration carries
  `ENVIRONMENT [[MIOPEN_USER_DB_PATH=...;PATH=<_rocm_sdk_core>\bin\;<inherited>]]`
  + `SKIP_RETURN_CODE "4"` (ctest_test\CTestTestfile.cmake).
- THE acceptance: ctest from the SAME clean environment that reproduced
  0xC0000135 now runs the test to a genuine **Passed** (0.14 s), 100%
  passed, ctest rc 0 — NOT skipped.
  Evidence: `evidence/phase5_1_r2/ci/fc24_fix_ctest_clean_env.json`.
- Loaded-DLL provenance (psutil module snapshot of the running test, clean
  PATH + only the CMake-derived dir): loaded
  `...\_rocm_sdk_core\bin\hiprtc0714.dll`, SHA256 c6159dd1… — exact match,
  correct ROCm 7.14 stack, no foreign version.
  Evidence: `evidence/phase5_1_r2/ci/fc24_dll_load_provenance.json`.
- Ordinary control PASS; positive no-STL PASS (5784-byte code object);
  13-cell adversarial matrix re-run: 13/13 PASS
  (`evidence/phase5_1_r2/ci/ci_matrix_phase5_1.json`, gate R25).
- Restricted-list parity re-verified (MIOPEN_TEST_BFLOAT16=ON fresh
  configure): `echo skipped` + DISABLED On, ctest ***Not Run (Disabled),
  rc 0 — identical to add_test_command's policy path.
- Exit-code fixture (0/1/2/4 → PASS/FAIL/FAIL/SKIP) unaffected.

## 6. Identity regeneration (per directive 9)

Commit 3 rebuilt: `61410b68` (tree `a65b040e`), message extended with the
runtime-directory sentence; commits 1/2 unchanged (trees still equal R1's).
R1→R2 source delta: projects/miopen/test/CMakeLists.txt only, +79/−16.
Patch series/hashes to be regenerated at Gate R29 from this state.

## 7. Subagent reviews

- A — Windows DLL loader / dependency provenance:
  evidence/phase5_1_r2/subagent_reviews/FC24_subagent_A_dll_provenance.md
- B — CMake/CTest portability & false-PASS:
  evidence/phase5_1_r2/subagent_reviews/FC24_subagent_B_portability.md
