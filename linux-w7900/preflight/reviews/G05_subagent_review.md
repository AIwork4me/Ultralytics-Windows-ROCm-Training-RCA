# G05 Independent Subagent Review — HIPRTC Compile-Output & Code-Object Provenance

- Reviewer: independent general-purpose subagent (fresh context)
- Date: 2026-10-08 (UTC)

## VERDICT: PASS

## Verified
- Code object sha256 79fd4f38... matches; 4728 bytes; ELF AMD GPU;
  target string `amdgcn-amd-amdhsa--gfx1100`
  (llvm-readobj Flags EF_AMDGPU_MACH_AMDGCN_GFX1100; axpy_smoke disassembles
  as valid GCN11).
- Smoke re-run: PASS, byte-identical fresh code object (cmp) vs archived.
- STL probe matrix reproduced exactly (utility=0 under both isolation flags;
  other three =1; all modes compile).
- Plain clang++ claim reproduced: all 4 headers not found under
  -nostdinc++/-nostdinc outside HIPRTC.
- dladdr provenance: wheel _rocm_sdk_core libhiprtc.so.7/libamdhip64.so.7;
  wheel dist-info rocm_sdk_core-7.14.1.
- Reviewer also demonstrated the environment-sensitivity of these tests
  (outside the isolated env, /opt/rocm 7.2.1 hiprtc loads) — reinforcing the
  mandatory env script discipline.

## Findings
- MINOR — the "actual #include <limits>" log lines were produced by an
  unarchived /tmp source. RESOLVED: source archived as
  scripts/g05_limits_include_test.cpp; evidence JSON updated.
- NIT — "7.14.60850" is the HIP toolchain version, not a libhiprtc
  self-report (hiprtcVersion()=9.0 API version). Labeling clarified in
  evidence JSON.

Gate G05 verdict: PASS.
