# G08 — Windows validation matrix — 2026-10-12

Platform: Windows 11, Radeon 8060S (gfx1151), ROCm 7.14 pip-wheel toolchain
(clang/hiprtc from _rocm_sdk_core; MIOpen built from source @ C:/b56p, discrete).

1. Clean CMake configure: PASS (proto_configure2.log; re-run after final rename OK)
2. Native gtest target builds: PASS — test_hiprtc_selfcontained.exe via glob
   registration, zero CMake edits (final_build2.log)
3. GTest discovery: PASS — binary lists CPU_HipRtcSelfContained_NONE.
   RtCompilesBatchNormWithoutHostStl (gtest_list.txt)
4. check_names.py: PASS — exit 0; schema OK; uniqueness 295 files 0 errors
5. CTest discovery: PASS under MIOPEN_TEST_ALL=ON — Test #111 registered
   (discrete gtest_discover_tests PRE_TEST; first listing run triggers
   discovery, entries persist). Under default Smoke filter the suite is
   intentionally not in the default entries — EXACT parity with the
   maintainer's own CPU_MiopenCstdintLP64_NONE (verified same-day, same
   build): CPU_* coverage comes from the YAML tier entries
   (miopen_gtest_{standard,comprehensive,full}[*_gfx115X] carry CPU_*
   patterns; standard carries the "pr" label).
6. Genuine no-host-STL precondition: CONFIRMED — P1 probe compiled under
   -nostdinc while P2 <type_traits>-use compiled ambient (probe pair in all runs)
7. Patched BN JIT compile: PASS (final_run1/2, postradix_run1/2)
8. Nonempty code object: PASS — module load during AddKernel; SaveBinary entries;
   standalone equivalent measured 5784 bytes (A/B log)
9. Unpatched negative control: PASS (see g07/) — FAIL + exact signature
10. Ordinary control: PASS (P0 trivial, every run)
11. With-STL control: PASS where supported (ambient BN compile both legs)
12. No phantom/duplicate test: reviewer-verified; target name unique after removal
13. Correct HIPRTC DLL: MIOpen.dll imports hiprtc0714.dll from _rocm_sdk_core/bin;
    runtime log "HIPRTC v.9.0"
14. Correct GPU arch: -mcpu=gfx1151 from live device in every compile
15. No unexpected skip: patched-tree runs PASSED (not skipped); forced-skip
    variant (G06) skipped ONLY when isolation defeated
16. No MIOpen runtime linkage failure: full build + runs green
17. MIOPEN_TEST_DISCRETE=ON validated end-to-end; =OFF verified at configure +
    build-graph level (miopen_gtest.obj includes the TU; miopen_gtest_check
    wired to check_names.py) per mission's representative-environment allowance
18. git diff --check: clean. clang-format (v23.1.3 --style=file): clean after
    in-place format (postradix_run2 re-validation after formatting)

DLL note: local runs needed the conda wheel's ROCm runtime DLL dirs on PATH
(hiprtc0714/rocblas/amdhip64 from _rocm_sdk_core + _rocm_sdk_libraries, and
libbz2/sqlite3 from dep_prefix) — a dev-machine artifact; on CI with a system
ROCm install these resolve natively. STL visibility is compiler-internal and
unaffected by PATH (probe-proven).
