# G01 Independent Subagent Review — ROCm Version Consistency & Library Contamination Audit

- Reviewer: independent general-purpose subagent (fresh context)
- Date: 2026-10-08 (UTC)

## VERDICT: CONDITIONAL PASS

All four primary claims verified TRUE when `scripts/env_rocm7141.sh` is
sourced. Isolation initially depended entirely on the env script.

## Verified
- /opt/rocm -> /opt/rocm-7.2.1 (version 7.2.1, HIP 7.2.53211, MIOpen 1.0.70201)
- /opt/venv torch libtorch_hip.so resolves all ROCm libs to /opt/rocm/lib
- env_rocm7141.sh correctly scrubs /opt/rocm from PATH/LD_LIBRARY_PATH;
  under it: hipcc 7.14.60850, torch 2.12.0+rocm7.14.1, rocm-sdk test 27/27 OK
- Under isolation, venv torch resolves libamdhip64/libhiprtc ->
  _rocm_sdk_core/lib and libMIOpen/librocblas/libhipblas -> _rocm_sdk_libraries/lib
- No 7.14.1 components leaked into /opt/rocm or /usr; only 70201-era dpkg pkgs
- pip check clean in both environments

## Findings
- MAJOR — venv torch isolation not self-contained: libtorch_hip.so RUNPATH
  contained only non-existent build-machine dirs; with
  `env -u LD_LIBRARY_PATH` it bound /opt/rocm-7.2.1 libs (contamination path
  demonstrated via ldd).
- MINOR — /etc/ld.so.conf.d/10-rocm-opencl.conf registers /opt/rocm-7.2.1/lib
  system-wide; env scripts cannot scrub ldconfig fallback.
- NIT — distro libamdhip64.so.5 (5.7.31921) present in /usr/lib (different
  SONAME; not loaded).

## Resolution during preparation (verified after fix)
- RUNPATH of 5 torch libs patched (patchelf); libtorch_hip.so (patchelf
  rejected) covered by $ORIGIN-first soname symlinks for all 8 required ROCm
  sonames in torch/lib.
- Post-fix proof: `env -i` python + CUDA init -> /proc maps show 100% in-venv
  ROCm libraries; zero /opt/rocm mappings. Device reported: AMD Radeon Pro
  W7900D.
- MAJOR finding closed. G01 final status: PASS (conditional resolved).
