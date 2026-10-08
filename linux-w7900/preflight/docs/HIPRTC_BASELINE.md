# HIPRTC Baseline — W7900 Linux Prep (gfx1100, ROCm 7.14.1 wheel SDK)

Date: 2026-10-08 | Gate: G05

## Toolchain under test

- libhiprtc.so.7 = 7.14.60850 (wheel `_rocm_sdk_core/lib`, dladdr-proven
  in every run; never /opt/rocm 7.2.1)
- libamdhip64.so.7 = 7.14.60850 (wheel `_rocm_sdk_core/lib`)
- Driver-level execution on the real W7900 (gfx1100)

## Smoke test (compiler control, not a patch regression test)

`scripts/g05_hiprtc_smoke.cpp`:

1. `hiprtcCreateProgram` + `hiprtcCompileProgram(-mcpu=gfx1100)` -> OK
2. Code object 4728 bytes (nonempty), archived at
   `evidence/G05_code_object_gfx1100.co`
   (sha256 `79fd4f38...d2ba7ca2`)
3. `hipModuleLoadDataEx` + `hipModuleLaunchKernel` of `axpy_smoke`
   -> 0/1024 mismatches, exit 0.

Log: `logs/G05_hiprtc_smoke.log` -> **PASS**

## STL-availability probe (the future A/B environment control)

`scripts/g05_stl_probe.cpp` executes an RTC kernel whose flags are read
back from GPU memory; plus a direct `#include <limits>` compile matrix.

| Mode | `<type_traits>` | `<utility>` | `<limits>` | `<initializer_list>` | actual `#include <limits>` |
|---|---|---|---|---|---|
| default | 1 | 1 | 1 | 1 | compiles |
| `-nostdinc++` | 1 | **0** | 1 | 1 | compiles |
| `-nostdinc` | 1 | **0** | 1 | 1 | compiles |

### Findings

1. **Default Linux HIPRTC exposes the full libc++ headers** (wheel LLVM
   `include/c++/v1`) to device compilation. This is why unpatched MIOpen
   HIPRTC kernels that pull `<limits>` / `<utility>` compile fine on Linux
   while the same code failed on Windows (Phase-3 RCA).
2. **`-nostdinc` and `-nostdinc++` are equivalent here and neither is a
   complete STL isolation method**: both remove only `<utility>`;
   `<type_traits>` / `<limits>` / `<initializer_list>` remain reachable
   through HIPRTC-internal include paths that survive both flags. (Plain
   `clang++` outside HIPRTC removes all four with either flag — verified.)
3. Consequence for the final validation protocol: any leg that must emulate
   the Windows "partial-STL" environment cannot rely on these flags alone on
   Linux. The normal A/B legs do NOT need that environment: on Linux both
   unpatched and patched builds compile; the single variable remains the
   MIOpen source patch.

## Scope honesty

This gate proves the HIPRTC compiler path works on gfx1100 with the exact
7.14.1 wheel library that the source-built MIOpen uses at runtime. It makes
NO claim about the no-host-STL MIOpen patch passing — that is future Phase-5.1
validation.
