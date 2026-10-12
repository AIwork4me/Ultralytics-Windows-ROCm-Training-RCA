# GTEST_ARCHITECTURE_DECISION — PR #13437 review thread r4247502213
# MIOPEN-PR13437-GTEST-ARCHITECTURE-CLOSURE-R1
Date: 2026-10-12 | Baseline: 64214f24 (five-commit chain verified)

Maintainer request (@averinevg): "Please use the existing runtime-compilation test
infrastructure, e.g. gtests like gtest/handle_test.cpp or gtest/miopen_cstdint_lp64.cpp,
instead of a standalone hipRTC test."

## Decision: DESIGN A — regression test via Handle::AddKernel in test/gtest/

`test/gtest/hiprtc_selfcontained.cpp`, single `TEST(CPU_HipRtcSelfContained_NONE, ...)`,
compiling the EMBEDDED production kernel MIOpenBatchNormFwdTrainSpatial.cpp through
`miopen::Handle::AddKernel` with `-nostdinc` isolation in `params`, gated by a
binary-outcome STL probe tri-state. Zero custom CMake (auto-registered by the gtest glob).

## Evidence-backed comparison

| Criterion | A: Handle::AddKernel (SELECTED) | B: gtest + direct hiprtc | C: standalone (status quo) |
|---|---|---|---|
| Maintainer compliance | Exactly the cited model (handle_test.cpp / miopen_cstdint_lp64.cpp both JIT via AddKernel with inline sources) | Partial: gtest ownership only; retains a parallel compile mechanism | None — explicitly rejected |
| Original bug coverage (R1) | STRONGER than standalone: compiles the real EMBEDDED production kernel source through the real production RTC path (options, named-header includes, cache) | Same as standalone (file-read source, own option set) | Real source file, own pathway |
| Genuine no-STL isolation (R2) | Via `-nostdinc` in params (verified to pass option filtering unchanged); probe proves it | Explicit -nostdinc + probe | Explicit -nostdinc + probe |
| Negative control (R4) | Unpatched tree → compile fails → miopen::Error → test FAILS (in-test). EXACT 'type_traits' signature verifiable only in external harness via MIOpen error log capture (in-process log not in exception) | Exact signature matchable in-test from hiprtc log | Exact signature in-test |
| Tri-state (R7) | Binary-outcome probe scheme P0/P1/P2 (below) — log text not observable through AddKernel | Direct log parsing | Direct log parsing |
| Windows portability | Native: DLL resolution/PATH handling all owned by MIOpen runtime; arch from live device (no gfx1151 hardcode) | Needs DLL PATH logic + arch selection (the removed CMake) | 130-line CMake + DLL PATH + arch cache var |
| Linux portability | Honest GTEST_SKIP when comgr injects host STL (P1 fail + P2 fail) | Same | Same (exit 4 → SKIP_RETURN_CODE) |
| CI discovery (R5,G12) | file(GLOB) auto-registration; *NONE* default filter; discrete+combined modes free | Needs custom target + discovery wiring | Manual add_test + EXCLUDE_TESTS glob surgery |
| CTest semantics | gtest_discover_tests standard path; skip semantics examined in G06 | Same + SKIP_RETURN_CODE config | Same |
| Build-time cost | One more TU in miopen_gtest_common-linked target; no new dependencies | New executable + hiprtc linkage | Current |
| Maintenance | ~200 lines, one file, no CMake | ~500 lines + CMake | 532 lines + 130-line CMake |
| Custom infra lines | 0 | ~40-80 (link, DLL, arch, skip mapping) | ~130 |

## Why A preserves the non-negotiable regression contract
- R1 real kernel: AddKernel with empty kernel_src uses the embedded production source
  (src/CMakeLists.txt registers MIOpenBatchNormFwdTrainSpatial.cpp; kernel_includes.cpp
  embeds the freestanding headers the fix added — they are exercised through their REAL
  registration, a stronger guarantee than the standalone's -I<kernels-dir>).
- R2 genuine isolation: -nostdinc passes BuildHip's option filter untouched (only -mcpu=*
  is stripped); the __has_include probe then PROVES unreachability before verdicts count.
- R3 positive: patched tree, probe proves isolation → BN compile must succeed and the
  module must load (hipModuleLoadData during AddKernel = code-object verification).
- R4 negative: unpatched tree → RTC fails ('type_traits') → binary empty →
  miopen::Error("Code object build failed") → gtest FAILs. In-test detection is
  guaranteed; the exact-signature proof belongs to the validation harness (G07) where
  MIOpen's error log is captured.
- R5 ordinary: P0 trivial-kernel compile through the same production path.
- R6 with-STL: P3 ambient compile asserted when the ambient probe (P2) shows STL reachable.
- R7 tri-state: P0 (toolchain sanity under isolation) / P1 (isolated probe) / P2 (ambient
  probe) — all binary outcomes, no log parsing needed:
    P1 compiles            → STL_UNREACHABLE → run main assertion
    P1 fails + P2 fails    → STL_REACHABLE   → GTEST_SKIP with explicit message
    P1 fails + P2 compiles → PROBE_BROKEN    → FAIL (fail-closed)
    P0 fails (± -nostdinc++ rescue attempt) → PROBE_BROKEN → FAIL
- R8 no false green/skip: Windows genuine no-STL → hard PASS; Linux injected-STL →
  honest skip (message states the no-STL condition was NOT tested); broken probe → FAIL,
  never a silent skip.
- R9 provenance: arch from the live device (LoadProgram -mcpu=<GetTargetProperties>),
  test binary and MIOpen library are the build outputs, DLL resolution native,
  module load proves code object.
- R10 platforms: same test source everywhere; behavior classified per environment.
- Stale-cache defense: per-run nonce option in params (cache key = name+params, not
  source content) → every run compiles fresh; no MIOPEN_DISABLE_CACHE process-global
  mutation (combined miopen_gtest binary safety).

## Design B rejected because
The maintainer asked for the EXISTING runtime-compilation infrastructure. B keeps a
second compile pathway, its own option set, kernel-source path resolution, DLL PATH
handling and arch selection — precisely the bespoke surface the review objects to —
merely wrapped in TEST(). It also duplicates what MIOpen already owns (include map,
option assembly, caching), creating drift risk.

## Design C rejected
Directly contradicts the review comment. Kept only as A/B baseline during prototyping
(G03) per mission.

## Residual risks (tracked)
1. In-test exact-signature assertion impossible (log swallowed by BuildHip) → G07
   harness captures MIOPEN_LOG_E/W stderr for the signature proof.
2. Kernel-cache pollution: nonce'd params add small cache entries per run — bounded,
   build-dir-scoped under ctest (MIOPEN_USER_DB_PATH), documented.
3. Non-RTC (file-based HipBuild) builds: probes still classify; expectation is honest
   skip or genuine behavior of that build — the fix's target path is RTC/comgr.
4. GPU required (get_handle + module load) — same requirement class as the maintainer's
   own miopen_cstdint_lp64.cpp; CPU_ naming per that precedent.
