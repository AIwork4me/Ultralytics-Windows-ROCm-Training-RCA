# CI AMENDMENT PROPOSAL — patch 0003 CTest portability (Phase 5.2.1 → Windows CodeX)

Status: PROPOSAL for the Windows CodeX side. The frozen canonical patch
(P5.1-CANDIDATE-R1, series sha256-pinned) was NOT modified in this
mission; re-freezing is CodeX's process, not ours.

Audience: Windows CodeX operator + upstream MIOpen maintainers.
Prepared from: Gate-C2 measurements on Linux W7900 / ROCm 7.14.1
(linux-w7900/phase5.2.1/findings/CTEST_PORTABILITY_ANALYSIS.md) and the
Windows Phase-5 CI integration evidence (docs/phase5/CI_INTEGRATION.md,
evidence/phase5/ci/*, all PASS on Windows gfx1151).

## Problem statement (three portability defects)

F-C2-1 — honest INCONCLUSIVE renders as CI failure.
The test's own capability probe (mandatory in isolated modes) returns
exit 4 INCONCLUSIVE when the host cannot reproduce the no-STL condition.
Linux ROCm 7.14.1 is such a host: libhiprtc-builtins.so.7 embeds
type_traits/limits/initializer_list, which remain reachable under every
isolation flag combination (B06 matrix, re-verified C2.5). With the
frozen registration (raw exit code = verdict), `ctest` reports
`***Failed`, `0% tests passed`, ctest rc 8 — a Linux CI leg with
BUILD_TESTING=ON goes RED although the patch is correct and both
executable controls (with-stl, ordinary) PASS.

F-C2-2 — the test target does not BUILD on Linux as registered.
Patch 0003 mirrors src/CMakeLists.txt's WIN32/non-WIN32 split and links
the PLAIN name `hiprtc` on non-WIN32. The hiprtc CMake package exports
ONLY the namespaced `hiprtc::hiprtc` imported target (INTERFACE_INCLUDE_
DIRECTORIES + IMPORTED_LOCATION); a plain-name link carries no usage
requirements, and the test target deliberately links nothing else (it
must not link MIOpen). Measured on Linux: `'hip/hiprtc.h' file not found`
at compile; after supplying the include dir, `unable to find library
-lhiprtc` at link. MIOpen's implementation target survives the plain
name only because it also links `hip::device`/`hip::host`.

F-C2-3 — add_test_command's Linux default discards the exit code
(discovered during Gate-3 mechanism validation).
Upstream `projects/miopen/test/CMakeLists.txt:96` defaults
`MIOPEN_TEST_GDB On` (Linux). In `add_test_command` (line 328) the
non-WIN32 GDB branch does NOT run the test binary directly; it generates
a `cmake -P` wrapper whose script is `execute_process(COMMAND <exe> …
RESULT_VARIABLE RESULT)` + `if(NOT RESULT EQUAL 0) … message(FATAL_ERROR
"Test failed")`. The wrapper collapses EVERY nonzero exit — including the
INCONCLUSIVE 4 — into a generic failure. Consequences, measured in the
isolated build tree (logs C2_ctest_run.log, C3_ctest_skip_demo.log,
C3_ctest_direct_noskip_counterfactual.log):

| registration                                   | property           | outcome                              |
|------------------------------------------------|--------------------|--------------------------------------|
| frozen: add_test_command (GDB wrapper, Linux)  | none               | ***Failed, ctest rc 8                |
| direct add_test (bypasses wrapper)             | none               | ***Failed, ctest rc 8                |
| direct add_test (bypasses wrapper)             | SKIP_RETURN_CODE 4 | ***Skipped, "100% passed", rc 0      |

Therefore `SKIP_RETURN_CODE 4` is NECESSARY BUT NOT SUFFICIENT while the
test is registered through `add_test_command` on Linux — the wrapper
never exits 4, so the property can never match. (Windows is unaffected:
the WIN32 branch registers the raw `$<TARGET_FILE>` command, exit codes
flow through — as evidenced by the Windows Phase-5 CTest PASS.)

## Proposed minimal amendment (exact, 2 hunks inside patch 0003)

Both changes live in the SAME CMake block patch 0003 already adds to
`projects/miopen/test/CMakeLists.txt`; the test source
`hiprtc_selfcontained.cpp` is untouched.

### Hunk 1 — capability-aware link (fixes F-C2-2)

Replace the platform split

```cmake
    if(WIN32)
        target_link_libraries(test_hiprtc_selfcontained PRIVATE hiprtc::hiprtc)
    else()
        target_link_libraries(test_hiprtc_selfcontained PRIVATE hiprtc)
    endif()
```

with a target-existence check (CMake-native capability detection):

```cmake
    if(TARGET hiprtc::hiprtc)
        target_link_libraries(test_hiprtc_selfcontained PRIVATE hiprtc::hiprtc)
    else()
        target_link_libraries(test_hiprtc_selfcontained PRIVATE hiprtc)
    endif()
```

Rationale: every modern ROCm CMake package (Windows wheel SDK, Linux
wheel SDK, distro ROCm) exports `hiprtc::hiprtc`; the plain-name arm
remains only as a fallback for packages that lack the namespaced target.
Windows behavior is unchanged (it already resolved to hiprtc::hiprtc);
Linux gains the imported target's include dir and link location, so the
target builds without any CI-side flag additions.

### Hunk 2 — direct registration + capability-aware skip (fixes F-C2-1 + F-C2-3)

Replace BOTH `add_test_command(...)` calls (both arch branches) inside
the same `if(MIOPEN_USE_HIPRTC)` block with direct `add_test`
registrations — the patch already registers this target manually (it
must not link MIOpen), so bypassing the repo helper's Linux GDB wrapper
is consistent with its own design — then set the skip property once:

```cmake
    if(NOT _hiprtc_test_arch STREQUAL "")
        add_test(NAME test_hiprtc_selfcontained
                 COMMAND test_hiprtc_selfcontained
                         ${CMAKE_CURRENT_SOURCE_DIR}/../src/kernels
                         --arch=${_hiprtc_test_arch})
    else()
        add_test(NAME test_hiprtc_selfcontained
                 COMMAND test_hiprtc_selfcontained
                         ${CMAKE_CURRENT_SOURCE_DIR}/../src/kernels)
    endif()
    # Parity with add_test_command's environment handling.
    set_tests_properties(test_hiprtc_selfcontained PROPERTIES
        ENVIRONMENT "MIOPEN_USER_DB_PATH=${CMAKE_CURRENT_BINARY_DIR}")
    # Exit 4 = INCONCLUSIVE: this host cannot reproduce the no-STL
    # condition (the test's embedded-STL probe found standard headers
    # still reachable under isolation). Report it as skipped instead of
    # failed — capability-aware, not platform-aware: hosts that CAN
    # isolate (e.g. the msvc-triple clang the fix targets) still get a
    # hard PASS/FAIL verdict from exit 0/1. Direct registration is
    # required on Linux, where add_test_command's MIOPEN_TEST_GDB
    # wrapper collapses every nonzero exit into a generic failure.
    set_tests_properties(test_hiprtc_selfcontained PROPERTIES SKIP_RETURN_CODE 4)
```

(`COMMAND test_hiprtc_selfcontained` with a target name resolves to the
built executable on all platforms; the explicit two calls keep the
existing arch/no-arch structure and avoid generator expressions.)

Mechanism: CMake test property `SKIP_RETURN_CODE` (present since CMake
2.8; MIOpen requires ≥ 3.15 — no version bump). CMake documents it
exactly for this case: "Sometimes only a test itself can determine if
all requirements for the test are met"; the given return code marks the
test as skipped ("Not Run"), neither pass nor fail. Empirically
validated in the isolated Linux build tree (C3_ctest_skip_demo.log):
exit 4 → `***Skipped`, `100% tests passed, 0 tests failed`, ctest rc 0,
test listed under "The following tests did not run … (Skipped)";
counterfactual without the property → `***Failed`, rc 8
(C3_ctest_direct_noskip_counterfactual.log).

## Requirement matrix (mission Gate-3 constraints)

| Requirement | How the amendment meets it |
|---|---|
| Windows with verified no-STL must still require PASS | Windows probe confirms STL unreachable → test proceeds; verdict is exit 0/1 → CTest PASS/FAIL (direct registration preserves raw exit codes on Windows exactly as the current WIN32 branch does). Exit 4 never occurs on an isolating host; nothing is weakened. |
| Linux with unavailable full isolation must report SKIP | Probe fires → exit 4 → SKIP_RETURN_CODE 4 → CTest "***Skipped"/Not-Run; leg stays green, skip visible in ctest summary; INCONCLUSIVE is never counted as PASS. Validated empirically (C3_ctest_skip_demo.log). |
| Ordinary/STL-present checks must remain executable | The binary's --mode=ordinary / --mode=with-stl invocations are untouched (they exit 0/1); default suite registration unchanged. Verified on Linux C2.4: with-stl PASS (6048-byte code object), ordinary PASS (3824-byte). |
| Do not change the frozen canonical patch in THIS mission | Proposal only; measured here with build-tree workarounds; the freeze (3eb20ec0…, tree 605d0d21…) re-verified intact. |
| Upstream-acceptable | Pure CMake, no workflow edits, no platform sniffing, no new options; mirrors CMake's own documented capability pattern; scoped to the block patch 0003 already adds. |

## Alternatives evaluated (and why not chosen)

1. `if(NOT WIN32)`-gated registration / DISABLED property — platform-
   hardcoding, not capability; would hide the test from future Linux
   hosts that CAN isolate, and from Linux no-STL regressions. REJECTED.
2. Make the test print SKIP and return 0 — destroys the honesty contract
   (exit 0 = PASS would let incapable hosts mint passes). REJECTED
   (explicitly forbidden: INCONCLUSIVE must never be PASS).
3. `SKIP_REGULAR_EXPRESSION "INCONCLUSIVE"` — same semantics via output
   text; more fragile (log noise / localization / future wording).
   DOCUMENTED FALLBACK only.
4. CI-side exit-code scraping in .github workflows — pushes repo logic
   into every consumer's CI; upstream-unacceptable. REJECTED.
5. Label-based per-OS ctest -E filtering — platform-based, requires
   workflow edits per leg. RANKED BELOW.
6. Configure-time compile-probe gating registration — heavier CMake,
   and registration-time capability can diverge from test-time reality.
   REJECTED for minimality.

## Re-freeze checklist for Windows CodeX

1. Apply the two hunks to the patch-0003 CMake hunk (test source
   unchanged); regenerate the patch (identical authorship/DCO rules).
2. Re-run the Windows P5-08 13-cell adversarial matrix — all 13 verdicts
   must be unchanged (exit 0/1 paths untouched; expect zero diffs).
3. Re-run the Windows CTest integration (configure/build/discover/run) —
   expect identical PASS; `ctest -N` still Test registration intact.
4. Optional cross-check on a Linux CI container: build target now
   succeeds WITHOUT external flags; `ctest -R '^test_hiprtc_selfcontained$'`
   ends "***Skipped"/Not-Run (rc 0), `--mode=with-stl` and `--mode=ordinary`
   still PASS. (Matches our C3 demonstration, which achieved this via
   build-tree-only CTestTestfile edits; the amendment bakes the same
   registration into the patch.)
5. Re-freeze as a new candidate revision (e.g. P5.1-CANDIDATE-R2) with
   new series sha256; update the Linux consumer manifest through the
   established handoff process. DO NOT mutate P5.1-CANDIDATE-R1 history.

## Explicitly out of scope

- Wiring --mode=negative / ordinary / with-stl into the default suite
  (unchanged upstream design decision; they remain A/B-harness tools).
- Any change to the test source's exit-code contract or probe logic.
- Any upstream PR/issue/comment from the Linux side (mission boundary).
