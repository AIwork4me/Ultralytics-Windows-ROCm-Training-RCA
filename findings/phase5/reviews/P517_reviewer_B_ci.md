# P517 — Reviewer B (CI maintainer) final audit of `test_hiprtc_selfcontained`

- Date: 2026-10-08
- Reviewer: CI maintainer (ROCm), independent re-execution; no prior verdict trusted
- CI commit: `39319c4d2f51998529dc0f2144841ba4cbe82ff3` (candidate worktree clean at HEAD)
- Scope: `projects/miopen/test/hiprtc_selfcontained.cpp` + registration in
  `projects/miopen/test/CMakeLists.txt:460-537`; build dir
  `phase5_build/ci_test` (Ninja, cmake 4.4.4); ctest from
  `phase3_buildtools/.../cmake/data/bin/ctest.exe`
- Provenance re-hashed by this reviewer:
  - binary `ci_test/bin/test_hiprtc_selfcontained.exe` =
    `6bc922596fdff45e4731d781483d00228785443ee3aaf6f0a800a3bb1ac15db` (matches matrix)
  - source `hiprtc_selfcontained.cpp` =
    `c97e748eebdd2b47a5efb97dce876f73b80a6e88615609075734422464313c80` (matches matrix)
  - `hiprtc0714.dll` = `c6159dd12714eed42c1d851e49a425404c1a34ba27cd2a8e721b0fe3db4fd86e` (matches matrix)

## VERDICT: CONDITIONAL PASS

Everything claimed for the audited (Windows, MIOPEN_USE_HIPRTC=ON) CI leg was
reproduced first-hand: real registration, real PASS, real A/B negative control,
fail-closed behavior on missing DLL. One MAJOR portability defect must be fixed
before this registration is allowed near a stock **Linux** ROCm CI leg: the
unconditional `hiprtc::hiprtc` link is a configure-time breaker on Linux where
the ROCm `hiprtc` package does not export that target. Two MINORs and NITs below.

## 1. What this reviewer re-executed (all commands run personally)

| Check | Command (abbreviated) | Result |
|---|---|---|
| Registration | `ctest -N -R test_hiprtc_selfcontained -V` | Test #10; command = `bin\test_hiprtc_selfcontained.exe "<src>/test/../src/kernels" "--arch=gfx1151"`; WORKING_DIRECTORY=ci_test/bin; env `MIOPEN_USER_DB_PATH` set |
| Positive run | `ctest -R "^test_hiprtc_selfcontained$" --output-on-failure` (PATH incl. `_rocm_sdk_core/bin`) | **Passed, 0.44 s, ctest exit 0** |
| Positive output | direct binary run, same argv | `PASS: kernel compiled without host STL (5784-byte code object)`, `code_size=5784`, exit 0; STL-unreachable probe held (no INCONCLUSIVE) |
| Missing-DLL control | same ctest, PATH stripped of `_rocm_sdk_core/bin` | **Failed**, `Exit code 0xc0000135`, ctest exit 8 — no false pass |
| negative/unpatched | binary vs pristine `7c586614` kernels, `--mode=negative --arch=gfx1151` | **exit 0**, signature `fatal error: 'type_traits' file not found` present exactly as sole error |
| negative/patched | same vs candidate `39319c4d` kernels | **exit 1**, `FAIL: no-STL compile unexpectedly succeeded` |
| Arch-selection snippet | exact registration logic exercised under cmake 4.4.4 script mode | suffix stripping, multi-target, fallback, empty-case all behave; no error path |
| CMP0028 semantics | stub project linking a nonexistent `hiprtc::hiprtc` | hard `CMake Error at ... target_link_libraries` (see M1) |
| Generated registration | `ci_test/test/CTestTestfile.cmake:25-26` | single `add_test`, absolute exe (`$<TARGET_FILE>` WIN32 form), argv contains **no** `--mode` |
| MIOPEN_USE_HIPRTC=OFF | attempted full configure with COMGR=OFF+HIPRTC=OFF | not feasible on this host: configure dies in `src/hipconv` (wheel hip-lang config) for reasons predating this change; **static analysis used instead** (below) |

## 2. Audit dimensions

### D1 — Real CMake integration: VERIFIED
- `file(GLOB TEST_SOURCES *.cpp)` (test/CMakeLists.txt:436) collects
  `hiprtc_selfcontained.cpp`; without `list(APPEND EXCLUDE_TESTS
  test_hiprtc_selfcontained)` (line 467, **unconditional**, outside the gate)
  the loop at 488-491 would call `add_test_executable` →
  `add_executable(test_hiprtc_selfcontained ...)` (line 361), colliding with the
  manual `add_executable` at line 504 → duplicate-target configure error. The
  exclusion is load-bearing and correctly placed before the glob filtering
  (474-486), and `EXCLUDE_TESTS` is `unset()` after use (481).
- `MIOPEN_USE_HIPRTC` is the real upstream option
  (projects/miopen/CMakeLists.txt:311), default = `MIOPEN_USE_COMGR`, and
  upstream enforces `MIOPEN_USE_COMGR == MIOPEN_USE_HIPRTC` (lines 313-316).
  `find_package(hiprtc REQUIRED)` lives inside the same gate
  (CMakeLists.txt:596-600), so the imported target exists exactly when the
  test's gate is open. Gate is correct.
- Link target: on this Windows leg it links the real imported
  `hiprtc::hiprtc` (provided here by the phase-3 shim
  `cmake_shims/hiprtc/lib/cmake/hiprtc/hiprtc-config.cmake`, an INTERFACE
  IMPORTED over `_rocm_sdk_core` lib/include). **But** upstream
  `src/CMakeLists.txt:1093-1099` links `hiprtc::hiprtc` only `if(WIN32)` and
  plain `hiprtc` otherwise — see M1.

### D2 — CTest registration: VERIFIED (with static-analysis caveat for OFF)
- `ctest -N` shows exactly one test, correct argv (kernels source dir +
  `--arch=gfx1151`), WIN32 `$<TARGET_FILE>` form confirmed in the generated
  CTestTestfile (line 25), working directory = KERNELS_BINARY_DIR, and the
  `MIOPEN_USER_DB_PATH` env property from `add_test_command` (harmless here).
- Skip lists: this configure's `SKIP_TESTS` =
  `db_sync;test_ctc;test_conv2d;test_conv2d_find2;test_immed_conv2d`
  (ci_configure.log:72) does not contain our test; `SKIP_ALL_EXCEPT_TESTS` is
  empty (line 73). `add_test_command`'s skip branch (`echo skipped` +
  `DISABLED On`) therefore did not fire — see m1 for the legs where it would.
- MIOPEN_USE_HIPRTC=OFF: the entire manual block (504-536) is inside the gate;
  the EXCLUDE_TESTS entry is unconditional so the glob creates nothing either;
  `add_dependencies` lines are inside the gate too. OFF ⇒ no target, no test,
  no ctest entry. (Dynamic OFF-leg configure is impossible on this Windows
  host for unrelated hipconv/hip-lang toolchain reasons; upstream's
  COMGR==HIPRTC invariant additionally means a true OFF leg is COMGR=OFF.)
  Note this is a silent coverage loss on OFF legs, not a failure — same as
  upstream treats every HIPRTC-dependent feature.

### D3 — Positive test: PASS (reproduced)
- Own ctest run: `1/1 ... Passed 0.44 sec`, exit 0. Direct run prints
  `PASS: kernel compiled without host STL (5784-byte code object)`;
  `[positive] create=0 compile=0 code=0 code_size=5784`. The STL-unreachable
  probe ran and held (an unreachable STL would have produced exit 4
  INCONCLUSIVE). Evidence log ci_ctest_run.log matches (0.16 s there; the
  0.68 s figure in CI_INTEGRATION.md does not match its own log — N4).

### D4 — Negative A/B control: VERIFIED, and cannot leak into the default suite
- `--mode=negative` appears nowhere in the registered argv
  (CTestTestfile.cmake:25) nor in any CMake code path. ctest `-R` regexes only
  select among registered tests and cannot inject arguments. SKIP_TESTS /
  SKIP_ALL_EXCEPT_TESTS only swap the command for `echo skipped` +
  `DISABLED` (ctest reports Not Run, never Passed). No test property anywhere
  rewrites argv (no PASS_REGULAR_EXPRESSION / WILL_FAIL / SKIP_REGULAR in the
  file — grep clean). **There is no mechanism by which a patched-tree CI run
  executes the negative expectation.**
- Matrix cells re-executed personally: negative/unpatched (pristine `7c586614`)
  exit 0 with the exact sole-error signature; negative/patched exit 1. Matches
  ci_matrix_phase5.json cells verbatim, including per-cell tree SHAs.

### D5 — False-pass resistance at the CTest level: VERIFIED
- `echo skipped`/DISABLED: would only apply via `add_test_command` if the name
  entered SKIP_TESTS/SKIP_ALL_EXCEPT_TESTS; DISABLED ⇒ "Not Run", not Passed
  (coverage-loss only — see m1).
- `FAIL_REGULAR_EXPRESSION "FAILED"` (add_test_executable, line 389) applies
  only to glob-registered tests; our test bypasses `add_test_executable`
  entirely, and the property can only convert exits into failures, never the
  reverse. No interaction.
- Binary-not-executing control: with the hiprtc DLL absent from PATH, ctest
  reported `Exit code 0xc0000135` → **Failed**, ctest exit 8. A test cannot be
  "Passed" without the process running and exiting 0.
- P508 (`findings/phase5/reviews/P508_false_pass_attack.md`) was read: its
  binary-level attacks (planted headers, CPATH, forged signatures, truncated
  kernels, duplicate args) all failed closed in the CI-wired configuration; its
  MINORs F1/F3/F4 have an explicit hardening disposition. This reviewer's
  CTest-level conclusions independently corroborate its section 7.

### D6 — Architecture selection: VERIFIED with two NITs
- Precedence `MIOPEN_TEST_HIPRTC_ARCH` → `GPU_TARGETS[0]` →
  `CMAKE_HIP_ARCHITECTURES[0]` → binary default gfx1151 confirmed live: this
  configure defines no GPU_TARGETS (not in cache / configure log), passed
  `-DCMAKE_HIP_ARCHITECTURES=gfx1151`, and the registered argv is
  `--arch=gfx1151` — the fallback chain's third arm demonstrably works.
- Snippet exercised verbatim under cmake 4.4.4 (script mode):
  `gfx1100:sramecc+`→`gfx1100`; `gfx90a:sramecc-:xnack-`→`gfx90a`;
  multi-target `gfx900;gfx906;gfx1100`→`gfx900` (first, deterministic);
  HIP-arch fallback→`gfx942`; nothing set→no `--arch` (binary default) with
  **no error** — the `if(GPU_TARGETS)`/`elseif(CMAKE_HIP_ARCHITECTURES)`
  guards prevent the `list(GET <empty> 0)` failure; `string(FIND/SUBSTRING)`
  semantics fine at any remotely modern CMake. No version issues.
- N2: an explicit `MIOPEN_TEST_HIPRTC_ARCH=gfxXXXX:features` bypasses suffix
  stripping (stripping is inside the empty-override branch) → hiprtc rejects →
  fail-visible. N3: `GPU_TARGETS=all` (if ever passed) would forward
  `--arch=all` → compile fails visibly. Both fail closed.

### D7 — Build dependency portability: one MAJOR, otherwise clean
- **M1 (below)**: `target_link_libraries(test_hiprtc_selfcontained PRIVATE
  hiprtc::hiprtc)` is unconditional. On stock Linux ROCm the `hiprtc` package
  does not define that target: ROCm/clr's `hipamd/src/hiprtc/CMakeLists.txt`
  (checked main and rocm-6.4.0) exports **only** `hiprtc-builtins` into the
  `hiprtc::` namespace (`INSTALL(EXPORT hiprtc-targets NAMESPACE hiprtc::)`);
  the `hiprtc` library itself is consumed by plain name (`-lhiprtc`) — exactly
  what upstream MIOpen does in `src/CMakeLists.txt:1093-1099`
  (`if(WIN32) hiprtc::hiprtc else() hiprtc`). Under CMP0028 (demonstrated with
  a stub under this cmake) a `::`-name with no target is a hard
  **configure error**, so a stock Linux HIPRTC+tests configure would die —
  taking the whole test suite with it, not just this test.
- GTest: not needed. The manual registration links only the hiprtc target;
  no `MIOpen_with_plugins`, no `Threads::Threads`, no GTest include paths; the
  source includes only `<hip/hiprtc.h>` + standard headers. The
  `-DGTest_DIR=...` in the configure is for the tree's other tests.
- WIN32 `NOMINMAX` (line 507-509) mirrors `add_test_executable`'s convention
  (362-364); no effect on Linux.
- `EXCLUDE_FROM_ALL` + `add_dependencies(miopen-tests/miopen-check)` (535-536)
  matches how every other test in this tree is built (all are EXCLUDE_FROM_ALL
  via line 361); the aggregates are the build entry points. No new requirement
  beyond what MIOPEN_USE_HIPRTC=ON legs already have (hiprtc package) — on
  Linux, once M1 is fixed, plain `hiprtc` linkage is satisfied by the same
  find_package already run by the gate.

## 3. Findings

| ID | Severity | Finding | Required action |
|---|---|---|---|
| M1 | **MAJOR** | Unconditional `hiprtc::hiprtc` link breaks stock Linux ROCm CI at configure time (CMP0028; ROCm's hiprtc package exports no `hiprtc::hiprtc` — verified against ROCm/clr main and rocm-6.4.0; upstream's own src/CMakeLists.txt:1093-1099 uses `hiprtc::hiprtc` only on WIN32, plain `hiprtc` otherwise). Loud failure of the entire test configure, not silent. | Mirror the upstream split in test/CMakeLists.txt:506: `if(WIN32) hiprtc::hiprtc else() hiprtc endif()`. Must land before any Linux leg. |
| m1 | MINOR | Legs with `MIOPEN_TEST_INT8=ON`, `MIOPEN_TEST_BFLOAT16=ON`, or `MIOPEN_NO_GPU=TRUE` set `SKIP_ALL_EXCEPT_TESTS` to lists that exclude this name, so `add_test_command` registers it as `echo skipped` + DISABLED → silently "Not Run" — coverage vanishes on exactly the cheap legs (incl. the no-GPU leg, where a compile-only test is most valuable). Not a false pass. | Either register outside `add_test_command` (plain `add_test`) or add the name to those lists' exceptions; at minimum document the leg matrix. |
| m2 | MINOR | The registration does not put the hiprtc DLL directory on PATH (ENVIRONMENT only sets `MIOPEN_USER_DB_PATH`); Windows ctest runs depend on the harness exporting PATH. Missing DLL fails closed (verified 0xc0000135 → Failed) — no false pass, but a spurious-red risk specific to this test (it is the only test whose binary loads hiprtc directly). | Consider `set_tests_properties(... ENVIRONMENT_MODIFICATION "PATH=path_list_prepend:...")` on WIN32, or keep the harness contract documented. |
| N1 | NIT | CI_INTEGRATION.md overstates "the same target src/CMakeLists.txt links" (true only for WIN32; Linux links plain `hiprtc`) — this wording hid M1. | Reword after M1. |
| N2 | NIT | Explicit `MIOPEN_TEST_HIPRTC_ARCH` value bypasses feature-suffix stripping (`gfx1100:sramecc+` forwarded verbatim → hiprtc rejects → fail-visible). | Strip unconditionally or document. |
| N3 | NIT | `GPU_TARGETS=all` (if a leg ever passes it) yields `--arch=all` → fail-visible compile error. | Optional guard. |
| N4 | NIT | CI_INTEGRATION.md quotes "Passed 0.68 s"; its own ci_ctest_run.log records 0.16 s. Also `ci_integration.json` has `test_exe: null` (script hashed `BUILD/` not `BUILD/bin/`; provenance preserved via matrix JSON). | Cosmetic. |
| N5 | NIT | `FAIL_REGULAR_EXPRESSION "FAILED"` (add_test_executable:389) is not applied to this test — irrelevant (exit code is the verdict; property can only add failures), but worth knowing the safety nets differ from glob-registered tests. | None. |

No BLOCKER findings. No false-PASS vector found at the CTest level: every
mechanism examined (skip lists, DISABLED, regex properties, missing DLL,
ctest -R selection) either preserves exit-code semantics or fails closed.

## 4. Conditions (for unconditional PASS)

1. Fix M1 (Linux target-name split) — one line, mirroring
   src/CMakeLists.txt:1093-1099.
2. Resolve or explicitly accept m1 (document the INT8/BF16/NO_GPU leg
   behavior).
3. (Carried from P508's conditions, endorsed: kernel-content marker,
   duplicate-arg rejection, four-header probe — these are test-source
   hardening, already dispositioned as TO BE HARDENED.)

## 5. Single most important CI improvement

Fix M1: make the hiprtc linkage platform-split exactly as upstream's
implementation does (`if(WIN32) hiprtc::hiprtc else() hiprtc`). As written,
the first stock-Linux HIPRTC test configure will fail in `test/CMakeLists.txt`
under CMP0028 and take the entire MIOpen test suite red — the worst possible
introduction for a regression test whose whole purpose is to be a reliable,
always-green CI guard on every HIPRTC leg.
