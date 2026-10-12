# G07 — Negative control (unpatched vs patched legs) — 2026-10-12

Both legs: same machine (Win11, Radeon 8060S gfx1151, ROCm 7.14 wheel toolchain,
clang from _rocm_sdk_core, HIPRTC reports v.9.0), same test source file
(test/gtest/hiprtc_selfcontained.cpp), same production pathway
(Handle::AddKernel → hiprtc::BuildHip, -mcpu=gfx1151 from live device),
same define set, nonce'd params (no kernel-cache reuse; verified by per-run
nonce in SaveBinary args and absence of LoadBinary hits).

LEG A (unpatched): C:/wa @ 54b079ca753bb3818017d5e724e208c03a43fd5a (PR base)
  + test file planted. Build C:/ba. Logs: legA_run1.log, legA_run2.log.
  Result: gtest FAILED (exit 1) at the MAIN isolated-BN assertion.
  Compile trail: trivial isolated SAVE, negative probe SAVE (isolation real),
  ambient STL-use SAVE, isolated BN FAIL (no SaveBinary), ambient BN SAVE.
  Failure signature (default log level, stderr):
    miopen_type_traits.hpp:151:10: fatal error: 'type_traits' file not found
    1 error generated when compiling for gfx1151.
  => single missing-stdlib error, in the exported (named-header) unpatched
  kernel header, under probe-proven -nostdinc isolation. The ambient with-STL
  compile of the SAME kernel SUCCEEDED on the same leg → failure is
  STL-specific, not a generic toolchain error. R4 satisfied.

LEG B (patched): C:/w56 @ 64214f24 (+ migration commits, test-only).
  Build C:/b56p. Logs: final_run1/2, proto_run4, postradix_run1/2.
  Result: gtest PASSED; isolated BN compiled and module loaded (code object
  produced; the standalone A/B on the same kernel/options measured a 5784-byte
  code object — proto_ab_standalone.log). All controls green.

Recorded identities:
  A_SOURCE_SHA=54b079ca753bb3818017d5e724e208c03a43fd5a
  B_SOURCE_SHA=64214f24756f117339c9d5c514f61d30d3853d3a (+ test-only commits a5b5197e,e271f6df)
  TEST_IMPL=identical test file both legs (planted copy, byte-identical)
  HIPRTC_VERSION=v.9.0 (hiprtc0714.dll, ROCm 7.14.60850)
  GPU_ARCH=gfx1151 (live device, -mcpu=gfx1151 in compile args)
  ISOLATION_STATE=-nostdinc; probe-proven (P1 compiled; P2 compiled => ambient STL usable)
  A_ERROR_DIAGNOSTIC="'type_traits' file not found" @ miopen_type_traits.hpp:151, 1 error
  B_CODE_OBJECT=isolated BN SaveBinary present + hipModuleLoadData OK (see final logs)
  STALE_CACHE=none (unique nonces per run; LoadBinary misses logged)
  TRIVIAL_KERNEL_SUBSTITUTION=none (embedded production source used; GetKernelSrc)
