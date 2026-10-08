# G04 Independent Subagent Review — Source SHA / Compiler / Dependency / Build Provenance

- Reviewer: independent general-purpose subagent (fresh context)
- Date: 2026-10-08 (UTC)

## VERDICT: CONDITIONAL PASS

## Verified
- (a) sha256 + size of install/baseline/lib/libMIOpen.so.1.0 exact match
  (6af347af...90697, 803390264 bytes).
- (b) CMakeCache.txt zero /opt/rocm references; offload-bundler + amdgcn
  assembler pinned into 7.14.1 wheel SDK (configure log lines confirmed).
- (c) MIOPEN_USE_HIPRTC=ON, COMGR=ON, CK=OFF, GPU_TARGETS=gfx1100,
  CMAKE_CXX_COMPILER = wheel amdclang++.
- (d) rocm_setup_version(VERSION 3.6.2) at projects/miopen/CMakeLists.txt:181;
  source/final-patched EMPTY; radix.hpp UNPATCHED (line 30 unconditional
  `#include <limits>`, no MIOPEN_HIP_RUNTIME_COMPILE guard around it).
- (e) Isolated env: hiprtc/amd_comgr/amdhip64 -> _rocm_sdk_core, rocblas ->
  _rocm_sdk_libraries (all 7.14.1).
- (g) Strengthened: full git-blob comparison of all 8032/8032 real files of
  source/upstream-pristine vs pinned commit b68f894 — IDENTICAL (fin/ is a
  submodule gitlink rendered as empty dir; expected for codeload tarball).

## Findings
- MAJOR-1 — Wheel libMIOpen.so.1 (MIOpen 3.5.2, _rocm_sdk_libraries) shadows
  the baseline build under env_rocm7141.sh alone: LD_LIBRARY_PATH outranks
  driver RUNPATH; `MIOpenDriver --version` reported 3.5.2 (wrong). RESOLVED
  during preparation: scripts/run_validation_leg.sh prepends leg install/lib
  and LD_PRELOADs the leg soname; corrected run logs
  logs/G04_mioopen_driver_version.log (3.6.2, correct ldd).
- MAJOR-2 — Venv devel/bin ships MIOpenDriver earlier in PATH. RESOLVED:
  absolute-path invocation rule encoded in runner scripts.
- MINOR — GPU_TARGETS recorded as UNINITIALIZED type in cache (value correct).
- NIT — libMIOpen.so has no embedded 7.14.1 RPATH pin (system-default ldd
  binds 7.2.1); acceptable because all validation runs use controlled env.

Gate G04 final: PASS (both MAJOR findings resolved same-session with
recorded proof).
