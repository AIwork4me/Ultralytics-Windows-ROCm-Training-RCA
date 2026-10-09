# Gate R21 — Independent Subagent Audit (CMake/CTest maintainer style)

Reviewer: fresh-context general-purpose subagent (agent_e2a3e323), read-only,
re-inspected every load-bearing file/line itself.

## VERDICT: PASS

Claims A–H all CONFIRMED from primary sources (helper test/CMakeLists.txt:327–354,
MIOPEN_TEST_GDB default On at :96 with no WIN32 guard; WIN32 branch raw exit codes
at :334–335; GDB cmake -P wrapper collapses every nonzero exit at :336–351;
trailing ENVIRONMENT at :353; MIOPEN_NO_GPU allowlist at :291–294; BUILD_TESTING
gate at parent :967/968; R1 block at :493–544 with link split :509–513 and two
add_test_command calls :535–540, zero set_tests_properties; shim exports only
hiprtc::hiprtc INTERFACE IMPORTED; test source exit contract 0/1/2/4 with STL
probe at :316–329, argv-derived absolute kernel path, no MIOpen link).

Design-sufficiency audit (claim H): CONFIRMED sufficient —
- F-C2-2 no-op on Windows: find_package(hiprtc) at parent projects/miopen/CMakeLists.txt:600
  runs before add_subdirectory(test):968 → TARGET hiprtc::hiprtc defined at block site.
- No ordering hole for an inline copy of the helper's guard: SKIP_TESTS/SKIP_ALL_EXCEPT_TESTS
  fully populated and frozen by line 323; zero writes after 330; block sits at 503–544.
  CMP0057 (IN_LIST) is NEW from line 27 → inline guard legal.
- Policy parity: MIOPEN_NO_GPU / INT8 / BF16 legs disable the test exactly as the helper would.
- Windows verdicts 0→PASS / 1→FAIL / 2→FAIL unchanged (no FAIL_REGULAR_EXPRESSION in either
  path; that property comes from add_test_executable:389, bypassed in both R1 and R2).
  Only delta: exit 4 → SKIPPED (the amendment's purpose; P5-08 CPATH cell).

Findings:
- MINOR #13: the R2 skip-list guard must wrap BOTH arch/no-arch add_test variants
  (whole if/else), not one branch. → Applied in Gate R22 implementation.
- NIT #14: `echo skipped` is a cmd builtin — but byte-identical to the helper's own
  disabled path already exercised on Windows legs (test_conv2d etc.); DISABLED On
  means it never spawns. No new risk.
- NIT #15: disabled-path ENVIRONMENT parity loss is inert (DISABLED test never runs).

Conclusion: proceed to implementation.
