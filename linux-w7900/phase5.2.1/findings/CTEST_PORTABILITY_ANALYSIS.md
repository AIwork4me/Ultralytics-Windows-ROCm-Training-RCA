# Gate C2 — CTest Portability Analysis (Phase 5.2.1)

Mission: close CI portability + reproducibility gaps before formal Linux
W7900 final A/B validation. Frozen candidate P5.1-CANDIDATE-R1; frozen base
7c5866144ac4b879be442563e2b49fa1c142ea36; canonical series verified by
sha256 BEFORE use (14719b8b… / 7d40c314… / 3eb20ec0…).

## C2.1 Frozen patch-0003 test source + CMake registration (inspection)

SOURCE-OF-TRUTH NOTE (independent-audit recommendation): the frozen series
is `patches/phase5_1/canonical/` ON the freeze ref
(`origin/phase5.1/windows-final-candidate-freeze` = 494907699f3b…).
The working tree on main also carries the SUPERSEDED P5-CANDIDATE-R1
series at `patches/phase5/canonical/` whose 0003 hashes 59306105… — do NOT
use it for identity checks; it differs by the documented From/index/
copyright-placeholder lines only.

`patches/phase5_1/canonical/0003-MIOpen-add-HIPRTC-no-host-STL-regression-test.patch`
(SHA256 3eb20ec0b4c38035438d317c210847e880ae8be5bf914617fb51f160f46670b4):

- Adds `projects/miopen/test/hiprtc_selfcontained.cpp` (532 lines) and a
  57-line hunk to `projects/miopen/test/CMakeLists.txt`.
- Registration is MANUAL (not via `add_test_executable`): the test drives
  hiprtc directly and must not link `MIOpen_with_plugins`.
  - `list(APPEND EXCLUDE_TESTS test_hiprtc_selfcontained)` keeps it out of
    the glob; then inside `if(MIOPEN_USE_HIPRTC)`:
    `add_executable(... EXCLUDE_FROM_ALL ...)`, platform-split link
    (`hiprtc::hiprtc` on WIN32, plain `hiprtc` elsewhere),
    `add_test_command(test_hiprtc_selfcontained ... ${kernels-src-dir}
    [--arch=...])`, plus `add_dependencies(miopen-tests/miopen-check ...)`.
  - `add_test_command` (test/CMakeLists.txt:328 upstream) is a plain
    `add_test(NAME ... COMMAND ...)` on non-WIN32: the test executable's
    process exit code IS the CTest verdict; no SKIP property is set
    anywhere in the frozen patch.
- Exit-code contract inside the test: 0=PASS, 1=FAIL, 2=SETUP,
  4=INCONCLUSIVE. Isolated modes run a mandatory STL-unreachability probe
  (`__has_include(<type_traits>)||(<utility>)||(<limits>)||(<initializer_list>)`
  with `#error STL_PROBE_REACHABLE`); if any header is still reachable the
  test prints `INCONCLUSIVE: host C++ stdlib still reachable ...` and
  returns 4 — by design, so a non-isolating host can never convert the
  positive mode into a false PASS.

## C2.2 Linux BUILD_TESTING=OFF configuration (confirmed)

- `scripts/build_leg_miopen.sh:49` hardcodes `-DBUILD_TESTING=OFF` for
  every validation leg (single-variable A/B discipline).
- `build/legA-frozen-miopen/CMakeCache.txt` (frozen Leg A):
  `BUILD_TESTING:BOOL=OFF`, `MIOPEN_USE_HIPRTC:BOOL=ON`, `GPU_TARGETS=gfx1100`.
- Upstream gating: `projects/miopen/CMakeLists.txt:967`
  `if(BUILD_TESTING) add_subdirectory(test)` — with OFF, patch-0003's
  registration file is never processed: the test is neither BUILT nor
  DISCOVERABLE on any Linux validation leg. (Discovery gap, not a failure.)

## C2.3 Isolated BUILD_TESTING=ON test build (how-to + executed)

Executed by `scripts/phase521_test_build.sh` (exact wrapper preserved in
`linux-w7900/phase5.2.1/wrappers/phase521_test_build.sh`):

1. Worktree `build/recon/phase521-test-tree` at `refs/phase52/frozen-base`
   + `git am` of the three canonical patches →
   `git write-tree` = `605d0d214acdbc06086fdb27c61fec970c0f2798` (EXACT
   frozen tree, same as Phase-5.2 B05; guard refuses otherwise).
2. Fresh isolated build dir `build/test-BUILD_TESTING-ON`; flags IDENTICAL
   to Leg A except the single functional delta `-DBUILD_TESTING=ON` (plus
   an isolated install prefix so the /opt/rocm cache guard stays
   meaningful). ROCm 7.14.1 wheel SDK env (`env_rocm7141.sh`);
   CMakeCache facts recorded (`C2_test_build_cache_facts.txt`):
   BUILD_TESTING=ON, MIOPEN_USE_HIPRTC=ON, GPU_TARGETS=gfx1100,
   CXX=venv amdclang++; 0 `/opt/rocm` entries (guard CLEAN).
3. Build ONLY `--target test_hiprtc_selfcontained` (no install, no other
   tests, no operational leg).

FINDING F-C2-2 (portability defect, frozen patch 0003, non-WIN32):
the plain-name `hiprtc` link carries no usage requirements, and the
hiprtc CMake package exports ONLY the namespaced `hiprtc::hiprtc` target
(INTERFACE_INCLUDE_DIRECTORIES …/include; no plain `hiprtc` target exists
— verified in the 7.14.1 SDK config). The upstream impl target survives
the plain name because it ALSO links `hip::device`/`hip::host`, which
supply the include path and -L; the test target deliberately links
nothing else. Result on Linux: compile fails `'hip/hiprtc.h' file not
found`; after supplying the include dir, link fails `unable to find
library -lhiprtc`. Measurement-harness workaround (build-tree only; the
frozen patch itself was NOT modified):
`-DCMAKE_CXX_STANDARD_INCLUDE_DIRECTORIES=$DEVEL/include
-DCMAKE_EXE_LINKER_FLAGS=-L$DEVEL/lib`.
Windows is unaffected (hiprtc::hiprtc carries includes/locations).

## C2.4 No-STL positive test on ROCm 7.14.1 — exit code verified

Test binary sha256: 9472c55ece2cbea6e4ca6cf7ff4511415658c99bfa11542e422e8d78815f4bd2
Direct mode matrix (logs `C2_direct_mode_*.log`):

| mode       | expectation                                  | actual exit | verdict                     |
|------------|----------------------------------------------|-------------|-----------------------------|
| positive   | patched kernel compiles under real no-STL    | 4           | INCONCLUSIVE (probe fired)  |
| negative   | unpatched signature failure under real no-STL| 4           | INCONCLUSIVE (probe fired)  |
| with-stl   | kernel compiles with ambient STL             | 0           | PASS (6048-byte code obj)   |
| ordinary   | trivial kernel through same hiprtc calls     | 0           | PASS (3824-byte code obj)   |

The INCONCLUSIVE is the patch's OWN honesty mechanism, exactly as
documented in the Phase-5.2 runbook: the embedded-STL probe detected
reachable headers under `-nostdinc` BEFORE any kernel verdict
(`STL_PROBE_REACHABLE` `#error` seen in the log). INCONCLUSIVE is NOT
counted as PASS anywhere in this mission.

CTest behavior with the frozen (unamended) registration
(`C2_ctest_discovery.log`, `C2_ctest_run.log`):
- discovery works: `Test #10: test_hiprtc_selfcontained`, Total Tests: 1;
- run: `***Failed 0.11 sec`, `0% tests passed, 1 tests failed out of 1`,
  ctest process exit code 8. I.e. an honest INCONCLUSIVE diagnostic is
  reported by CTest as a plain FAILURE → any Linux CI leg with
  BUILD_TESTING=ON goes red although the patch is fine and both
  executable controls pass. This is the CI portability gap Gate 3
  addresses.

## C2.5 Independent header-availability audit (B06 probe re-run)

`build/kthvalue-harness/b06_probe` (Phase-5.2 B06 probe, re-executed
under env_rocm7141.sh, GPU W7900D present; log
`C2_b06_probe_header_audit.log`):

- default flags: type_traits=1 utility=1 limits=1 initializer_list=1
- `-nostdinc++`, `-nostdinc`, `-nostdinc++ -nobuiltininc`,
  `-nostdinc -nobuiltininc`, `-nostdinc -nobuiltininc --sysroot=…`:
  ALL yield [1 0 1 1] — type_traits/limits/initializer_list remain
  reachable (embedded in libhiprtc-builtins.so.7), only utility becomes
  unreachable; every mode's control kernel COMPILED+RAN (probe healthy).
- Conclusion: full host-STL isolation is NOT reproducible on Linux
  ROCm 7.14.1; consistent with Phase-5.2 B06/B07 and with the exit-4
  measured in C2.4. The no-STL regression evidence remains the Windows
  run; Linux must report SKIP (Gate 3), never PASS, for the isolated
  modes.

## Exit summary

- CTest discovery: WORKS under BUILD_TESTING=ON (F-C2-2 build workarounds
  needed on Linux); NOT built/discovered under the legs' BUILD_TESTING=OFF.
- Actual exit code, no-STL positive, ROCm 7.14.1: 4 (INCONCLUSIVE);
  CTest unamended renders it Failed (ctest rc 8).
- with-stl / ordinary controls: PASS (exit 0) — executable on Linux.
- Frozen patch 0003 content: UNCHANGED (series sha256 re-verified before
  and after the mission; worktree discarded after measurement).
