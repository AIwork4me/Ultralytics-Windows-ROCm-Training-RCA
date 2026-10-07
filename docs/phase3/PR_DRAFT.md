# PR DRAFT — NOT SUBMITTED (Gate 82)

**Title**: MIOpen: keep runtime-compiled kernels self-contained when no
host C++ standard library is reachable

**Summary**

Runtime-compiled (HIPRTC) MIOpen kernels currently require a reachable
C++ standard library on HIP >= 7: `miopen_type_traits.hpp` (since #3803)
and `miopen_utility.hpp` (since #3147) disable the internal no-STL
compatibility shims for `HIP_PACKAGE_VERSION_FLAT >= 7000000000` and
unconditionally include the real headers. On AMD's Windows pip wheels the
bundled msvc-triple clang/hiprtc ships no C++ stdlib and no
include-path configuration, so every runtime-compiled kernel compile
fails (`fatal error: 'type_traits' file not found` →
`HIPRTC_ERROR_COMPILATION`), which PyTorch surfaces as
`miopenStatusUnknownError` (issue #3956; also seen in AMD's Windows
release-wheel CI, TheRock#8292).

This PR restores kernel-source self-containment WITHOUT changing
STL-present behavior: when a real std header is reachable
(`__has_include`), use it exactly as today; when it is not, use new
self-tested freestanding headers. The HIP < 7 legacy shim arms are left
byte-identical.

**Problem / Root cause / Fix**: see the attached maintainer report
(`MAINTAINER_REPORT_DRAFT.md` content).

**Files changed**

```
projects/miopen/src/kernels/miopen_type_traits.hpp        (probe in HIP>=7 RTC arm)
projects/miopen/src/kernels/miopen_utility.hpp            (same)
projects/miopen/src/kernels/miopen_freestanding_type_traits.hpp   (new)
projects/miopen/src/kernels/miopen_freestanding_utility.hpp       (new)
projects/miopen/src/kernels/miopen_freestanding_initializer_list.hpp (new)
projects/miopen/src/kernels/radix.hpp                      (RTC: miopen_cstdint instead of <limits>)
projects/miopen/src/kernels/tensor_view.hpp                (probe for <initializer_list>)
projects/miopen/src/CMakeLists.txt                         (embed-list registration)
```

Full diff: `patches/phase3/0001-miopen-hiprtc-selfcontained.patch + 0002-miopen-hiprtc-selfcontained.patch (two-commit series)`.

**Testing**

- Negative control: unpatched develop + hiprtc `-nostdinc` → reproduces
  `'type_traits' file not found` at `miopen_type_traits.hpp:151`.
- Patched: same compile exits 0; freestanding traits carry static_assert
  self-tests; GPU-executing canaries verify every trait at runtime.
- Full patched build on Windows (gfx1151, ROCm 7.14 wheel toolchain),
  loaded by PyTorch with SHA-proven provenance: BatchNorm matrix (6
  variants + 5 controls) numerically correct vs CPU (≤ 9.5e-7); 11-op
  non-BN RTC matrix green; YOLO26n coco8 1-epoch training green in both
  amp modes — all with the machine's MSVC include tree renamed away (no
  host STL), and re-verified with it present.
- Static audit of all 104 RTC kernel entries × std usage committed as a
  reusable script.

**Risk**

- Whole-STL-present environments (all of Linux, Windows+MSVC): the probe
  takes the real-STL branch — behavior identical to current develop;
  HIP<7 RTC arms untouched; offline builds untouched.
- The freestanding arm only executes where compilation previously always
  failed (strictly-better).
- Coexistence of freestanding definitions with a real STL in one TU is
  prevented by construction: `__has_include` tests search-path existence
  (TU-global), and deliberately inconsistent partial-STL states fail
  LOUDLY (`#error`) rather than double-defining — the #7718 failure class
  cannot recur silently.
- Requires `__has_include` in the RTC compiler (standard C++17; all
  supported clang toolchains have it — a compiler lacking it would
  misselect the freestanding arm; not known to exist in MIOpen CI).
- Probe outcome is machine-state-dependent: identical MIOpen binaries may
  take different arms on different machines; no semantic difference for
  the audited entity set, but kernel-cache provenance differs across STL
  states.

**Remaining before merge**: Linux HIP>=7 regression runs (author lacks a
Linux ROCm GPU environment; analysis says no behavior change where STL is
reachable).

**Related issue**: #3956. Related context: #7718, rocRAND PR #8247,
TheRock#8292.

---

*Prepared as part of an independent RCA
(AIwork4me/Ultralytics-Windows-ROCm-Training-RCA, Phase 3). No upstream
submission has been made.*
