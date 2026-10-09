# CTEST PORTABILITY — R2 `test_hiprtc_selfcontained` on Linux ROCm 7.14.1

## What R2 fixed (F-C2-1/2/3 from Phase 5.2.1)

1. **Capability-aware link** — `if(TARGET hiprtc::hiprtc)` else plain `hiprtc`
   (test/CMakeLists.txt:517-521). On this host the package exports the namespaced target.
2. **Direct `add_test` registration** bypassing `add_test_command`'s MIOPEN_TEST_GDB
   wrapper (which folds every nonzero exit into generic failure; lines 550-558).
3. **`SKIP_RETURN_CODE 4`** on the real registration (lines 611-613): exit 4 =
   INCONCLUSIVE = "this host cannot reproduce the no-STL condition" renders as Skipped,
   never Failed, never PASS.

## Measured on the R2 tree (build/recon53-test, BUILD_TESTING=ON, HIPRTC ON, gfx1100)

- Target builds in 3 ninja steps **without** the Phase-5.2.1 measurement workarounds
  (NO `CMAKE_CXX_STANDARD_INCLUDE_DIRECTORIES`, NO `CMAKE_EXE_LINKER_FLAGS`).
- `ctest -N -R '^test_hiprtc_selfcontained$'`: Test #10 discovered, rc 0.
- `ctest --output-on-failure -R '^test_hiprtc_selfcontained$'`:
  `***Skipped 0.05 sec`, `100% tests passed, 0 tests failed out of 1`,
  `The following tests did not run: 10 - test_hiprtc_selfcontained (Skipped)`,
  **ctest process exit 0**.

## Direct binary mode matrix (arch gfx1100)

| Mode | Kernels | Exit | Verdict |
|---|---|---|---|
| ordinary | R2 | 0 | PASS (3824-byte code object) |
| with-stl | R2 | 0 | PASS (6048-byte code object) |
| positive | R2 | 4 | INCONCLUSIVE — probe fired `stl_probe.cu:2:2: error: STL_PROBE_REACHABLE` → "host C++ stdlib still reachable under -nostdinc" |
| negative | Leg A (unpatched) | 4 | INCONCLUSIVE — isolation prerequisite unsatisfied on this host |

## False-skip audit

- The executable really launched (0.05 s runtime; LastTest.log carries its own output).
- It reached the isolation probe (raw diagnostic above).
- Exit 4 is the skip reason (SKIP_RETURN_CODE 4 property verified in CTestTestfile).
- Exit 1/2 remain hard failures (fixture: 1→Failed rc 8, 2→Failed rc 8).
- Not a disabled test masquerading: the BF16 restricted configure shows what disabled
  registration looks like (`echo skipped` + DISABLED On) — different mechanism, verified.
- Exit-code mapping fixture (independent cmake project): 0→Passed/ctest rc 0,
  1→Failed/8, 2→Failed/8, 4→Skipped/0.

## Honest scope

On stock Linux ROCm (7.14.1) full no-STL isolation is not reproducible because
libhiprtc-builtins embeds the C++ headers. **SKIPPED IS NOT A no-STL PASS.** The Windows
matrix ground truth (positive=1 FAIL on unpatched, negative=0 PASS on patched) remains
Windows-side evidence. If a future toolchain makes isolation possible, investigate before
accepting a genuine PASS (mission rule).
