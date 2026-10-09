# HIPRTC / CTest behavior on Linux gfx1151 (Gate H03)

Build: `test_hiprtc_selfcontained` from the exact R2 tree (b983cad) with
BUILD_TESTING=ON, MIOPEN_USE_HIPRTC=ON, GPU_TARGETS=gfx1151, wheel 7.14.0
toolchain. NO manual HIPRTC include/lib injection — the R2 CMake
portability fix (capability-aware hiprtc::hiprtc link) carried configure,
build, and link alone. Package-LOCATION hints (-Dhip_DIR etc.) are the
Phase-3-mandated wheel-pinning against /opt/rocm-7.2.1, not include/lib
injection. Target sha256 4470c896…, links wheel libhiprtc.so.7
(cdee97e0…), zero /opt/rocm in CMakeCache.

Results (evidence/ctest_matrix.json, logs/h03_*.log):

| Mode | Exit | Meaning |
|---|---|---|
| default (positive/no-STL) | 4 | INCONCLUSIVE — stdlib still reachable under -nostdinc (comgr staging); auditor reproduced with an independent driver |
| --mode=ordinary | 0 | PASS (3824-byte code object) |
| --mode=with-stl | 0 | PASS (MIOpenBatchNormFwdTrainSpatial.cpp, 5792-byte object, gfx1151) |
| --mode=negative vs frozen legA kernels | 4 | INCONCLUSIVE per the verified (unavailable) isolation |

CTest: `ctest -R '^test_hiprtc_selfcontained$'` -> **Skipped**, "100% tests
passed, 0 tests failed", process exit 0 — because CMake registered
`SKIP_RETURN_CODE 4`; exit 1 would still be FAIL. SKIPPED is NOT counted as
a no-STL PASS; the Windows RCA owns the FAIL→PASS claim.

Classification: REAL NO-STL UNAVAILABLE on Linux + ROCm 7.14.0 wheel
(same class as W7900/7.14.1). Per-header nuance from the audit:
type_traits/limits/initializer_list reachable under -nostdinc; utility is
not — the probe's OR-list still fires.
