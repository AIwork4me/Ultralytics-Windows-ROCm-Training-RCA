# Linux STL Baseline — Gate L16

Date: 2026-10-07
Machine: HP ZBook Ultra, Ryzen AI MAX+ PRO 395, Radeon 8060S (gfx1151), Ubuntu 24.04.4, kernel 6.17.0-1032-oem

Note: "libhiprtc 9.0" is the library's self-reported `hiprtcVersion()` inside
the ROCm 7.14 wheel stack (file libhiprtc.so.7, build 7.14.60850) — recorded
as reported. Also note the host-mode driver probe (`amdclang++ -E -v` without
offload) fails to find `<type_traits>` (rc=1) because it uses the C-only
search list — only the HIP-offload list adds libstdc++; that is the relevant
mode for RTC device compilation and it is the one cited below. The `-H` trace
run through hiprtcCompileProgram escapes to process stderr, not the program
log: the raw trace is preserved in
evidence/phase3/raw/linux/hiprtc/which_stl_hiprtc_trace.txt (and as
which_stl_raw_polluted.json despite its .json extension); the program-log copy
inside which_stl.json is legitimately empty.

## Question

Why does the Linux ROCm 7.14 wheel stack's HIPRTC resolve `#include <type_traits>`
(and the other MIOpen spatial-BN std headers) when the identical Windows wheel stack cannot?

## Direct evidence (HIPRTC level)

`scripts/phase3/linux/hiprtc_which_stl.py` compiles `#include <type_traits>` through
`hiprtcCompileProgram` (wheel `libhiprtc.so.7`, version 9.0, gfx1151) with clang's
`-H` include trace passed through as an RTC option.

Trace (evidence/phase3/raw/linux/hiprtc/which_stl_hiprtc_trace.txt):

```
. /bin/../lib/gcc/x86_64-linux-gnu/13/../../../../include/c++/13/type_traits
.. .../include/x86_64-linux-gnu/c++/13/bits/c++config.h
... /usr/include/features.h           <- glibc, absolute
. <built-in>
.. /tmp/comgr-*/include/hiprtc_runtime.h   <- comgr-injected HIPRTC header
```

`<type_traits>` resolves to the **GCC 13 libstdc++** installation:
`/usr/lib/gcc/x86_64-linux-gnu/13/../../../../include/c++/13` = `/usr/include/c++/13`
(system g++ 13.3.0 is installed on this machine).

The wheel does NOT bundle a GCC-style header tree (no `lib/gcc/...` under
`_rocm_sdk_core` or `_rocm_sdk_devel`). The wheel does ship a libc++ at
`_rocm_sdk_core/lib/llvm/include/c++`, but the RTC trace shows it is NOT the
provider for HIPRTC device compilation.

## Supporting evidence (compiler-driver level)

`amdclang++ --offload-arch=gfx1151 -x hip -E -v` reports the device C++ search list
including, in order:

1. wheel clang resource dir (`.../_rocm_sdk_devel/lib/llvm/lib/clang/23/include/cuda_wrappers`)
2. `/usr/lib/gcc/x86_64-linux-gnu/13/../../../../include/c++/13`
3. `/usr/lib/gcc/x86_64-linux-gnu/13/../../../../include/x86_64-linux-gnu/c++/13`
4. `/usr/lib/gcc/x86_64-linux-gnu/13/../../../../include/c++/13/backward`
5. wheel clang resource include, `/usr/local/include`, `/usr/include/...`

This is clang's standard automatic GCC-installation detection (`--gcc-install-dir`
semantics): on Linux with system g++ present, AMD clang adds libstdc++ headers
automatically. On Windows there is no equivalent GCC/MSVC installation for the
`x86_64-pc-windows-msvc` clang to detect — the Phase-2 Windows RCA established
that no STL was found at any searched location.

Per the gate rules, the driver output alone would be supporting evidence only;
here the HIPRTC `-H` trace independently proves the same resolution inside the
actual RTC compile.

## Conclusion

Linux baseline STL provider for MIOpen HIPRTC device compiles =
**system GCC 13.3.0 libstdc++ headers (`/usr/include/c++/13`), auto-detected by
AMD clang inside comgr/HIPRTC**.

This is why the standalone HIPRTC header matrix (Gate L15) passes 6/6 on Linux.

Implication for Phase 3: the Windows candidate patch removes/overrides the
`<type_traits>` etc. dependencies in MIOpen RTC sources. On Linux the patch must
not break the currently-working system-libstdc++-backed path. The no-STL canary
(Gate L33, `-nostdinc++`-style isolation) exists precisely because ordinary
Linux PASS cannot distinguish "patch provides freestanding facilities" from
"system STL still masking them".
