# MIOpen runtime-compiled kernels fail without a host C++ standard library on Windows

## Problem

On AMD ROCm PyTorch pip wheels for native Windows (e.g. torch
2.12.0+rocm7.14.0, Radeon 8060S/gfx1151; also reported on gfx1200 with
rocm 7.2.1 in #3956), every spatial BatchNorm fails at first use:

```python
import torch, torch.nn as nn
m = nn.BatchNorm2d(16).cuda().train()
y = m(torch.randn(8, 16, 64, 64, device="cuda"))
# RuntimeError: miopenStatusUnknownError
```

with the underlying compiler error:

```
MIOpen(HIP): Error [Compile] hiprtcCompileProgram(...) MIOpenBatchNormFwdTrainSpatial.cpp:
HIPRTC_ERROR_COMPILATION (6)
miopen_type_traits.hpp:151:10: fatal error: 'type_traits' file not found
```

## Minimal reproducer

The 5-line snippet above (no Ultralytics/other frameworks needed).
Standalone ctypes HIPRTC probe (no torch/MIOpen at all) reproduces for
every std header: `<type_traits> <utility> <limits> <cstdint>
<initializer_list>`.

## Environment

- Windows 11, AMD Radeon 8060S (gfx1151), ROCm 7.14.0 pip wheels
  (`_rocm_sdk_core`/`_rocm_sdk_libraries`), torch 2.12.0+rocm7.14.0,
  MIOpen 3.5.2 — **no Visual Studio C++ toolchain installed** (stock
  consumer machine).
- Same signature externally: #3956 (gfx1200, 7.2.1, Py3.12) and AMD's own
  Windows release-wheel CI (TheRock#8292, torch release/2.12+2.13).

## Root cause

The Windows wheels ship an `x86_64-pc-windows-msvc`-target clang + hiprtc
with no C++ standard library and no include-path configuration; on
Windows, hiprtc leaves std-header resolution to clang's MSVC
auto-discovery, which finds nothing on a machine without VS Build Tools.

MIOpen's kernel headers assumed an STL is always reachable for HIP >= 7:
commit `ce14dab3` (PR #3803) wrapped `miopen_type_traits.hpp` — and
commit `b514736610` (PR #3147) independently wrapped
`miopen_utility.hpp` — so that for `HIP_PACKAGE_VERSION_FLAT >=
7000000000` the internal no-STL compatibility shims are disabled and real
`<type_traits>`/`<utility>` are included **even in runtime-compile mode**
(`MIOPEN_HIP_RUNTIME_COMPILE`). That assumption holds on Linux (system
STL reachable) but not on stock Windows wheel installs.

## Why HIP >= 7 exposes it

Pre-7, runtime-compiled kernels used MIOpen's internal freestanding
shims; the two HIP-7 PRs removed them under the then-new hiprtc design
direction ("RTC consumers include the real STL" — traits moved to
`__hip_internal` in hiprtc 7.0). The #3803-era shim is additionally
version-rotted (window-gated trait block; `__hip_internal::enable_if`
bridge), so simply re-enabling it does not work — the shim needs repair.

## Fix

Keep the real STL whenever it is reachable; use freestanding definitions
only when it is not — probed per-translation-unit with `__has_include`:

```cpp
#ifdef MIOPEN_HIP_RUNTIME_COMPILE
#if HIP_PACKAGE_VERSION_FLAT < 7000000000ULL
    /* legacy pre-7 shim (unchanged) */
#elif __has_include(<type_traits>)
#include <type_traits>                  /* Linux, Windows+MSVC: unchanged */
#else
#include "miopen_freestanding_type_traits.hpp"  /* no STL anywhere: new */
#endif
#else
#include <type_traits>                  /* offline builds: unchanged */
#endif
```

`miopen_utility.hpp` gets the same treatment; `radix.hpp`'s unguarded
`<limits>` routes to the existing `miopen_cstdint.hpp` in RTC mode;
`tensor_view.hpp`'s `<initializer_list>` gets the same probe. Three new
self-tested freestanding headers carry the trait set the RTC kernel
population uses (Gate-54 audit: `is_same`, `conditional`, `enable_if`,
`remove_reference/_cv`, `true/false_type`, `integral_constant`,
`is_pointer`, `is_trivially_copyable` (clang builtin), `forward`,
`initializer_list`).

The design cannot regress STL-present environments: wherever the real
headers resolve, the patched wrappers evaluate identically to current
develop. It also structurally prevents the #7718 failure class (shim
definitions coexisting with a real STL → `std::forward` redefinition),
since the freestanding arm is selected only when no real header resolves.

## Tests

- No-STL negative control (unpatched): pristine develop tree, hiprtc,
  `-nostdinc` → exact `'type_traits' file not found` failure.
- No-STL positive (patched): same compile with the patch → exit 0,
  correct code object; every freestanding trait also runtime-verified on
  GPU (static_assert self-tests + executing canaries).
- Real-build validation (Windows, gfx1151): patched MIOpen built from
  develop with the wheel toolchain, loaded by PyTorch (SHA-proven), then:
  BatchNorm train/eval across shapes (minimal / #3956 / YOLO-like / BN1d
  3D / BN2d / BN3d), numerics vs CPU ≤ 9.5e-7 max abs; 11-op non-BN RTC
  matrix (pooling, PReLU, conv variants incl. depthwise/grouped/dilated/
  transpose/1×1); YOLO26n coco8 1-epoch training both amp modes. All
  PASS — with the machine's MSVC include tree renamed away (no host STL),
  and re-verified with it present.

## Windows results

All of the above (see repo evidence index); single-variable A/B: only the
MIOpen.dll differs between failing control (wheel build) and passing
treatment (patched build) under identical no-MSVC state.

## Linux results

**Not yet run — no Linux ROCm GPU environment available to the author.**
Analysis (see PATCH_DESIGN.md): on Linux the probe takes the real-STL
branch, byte-identical to current behavior; the freestanding arm only
activates where compilation previously always failed. Linux HIP>=7
regression runs remain a precondition for merge.

## Regression coverage

- Full RTC-kernel × std-entity static audit (104 kernel entries) committed
  as a reusable script; patch covers all std needs of the PyTorch-reachable
  kernel set; the audit names the remaining driver-only paths (kthvalue et
  al.) which V2 also covers via tensor_view/radix routing.
- Non-RTC/offline builds unchanged (real STL path untouched).

## Related issue

MIOpen#3956 (identical signature, open, unanswered). Related: #7718
(mirror failure that motivates the availability-probe design), rocRAND
PR #8247 (same self-containment fix pattern, merged), TheRock#8292 (AMD
CI reproduction).

## Remaining limitations

- Linux HIP>=7 regression runs pending (blocking for merge).
- `__has_include` is required in the RTC toolchain (true for all clang
  MIOpen supports; called out for exotic vendors).
- The wheel-packaging gap itself (no bundled STL) is a separate,
  TheRock-owned issue; this fix makes MIOpen's kernels immune to it, not
  other components.
