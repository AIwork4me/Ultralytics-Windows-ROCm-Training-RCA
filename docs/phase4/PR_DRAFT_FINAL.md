# PR DRAFT — FINAL (Gate P55) — NOT SUBMITTED

**Title**: MIOpen: keep runtime-compiled kernels self-contained without a
host C++ standard library

**Status**: provisional two-commit series reconstructed and revalidated
(Phase 4); DCO pending human confirmation; NO PR created.

**Branch** (local only): `prepare/miopen-hiprtc-selfcontained`
= `b68f8944300f104875d953fc8e4510908c9aaf0b` (ROCm/rocm-libraries develop,
2026-10-07) + 2 commits:

1. `c86d1b9` — *MIOpen: keep RTC type traits self-contained when no host
   STL is reachable*
2. `4084759` — *MIOpen: make remaining RTC kernel std includes
   self-contained*

Optional third commit (CI test; PROPOSAL artifact only, not yet a
prepared branch): *MIOpen: test HIPRTC compilation without host C++
STL* — see `docs/phase4/CI_REGRESSION_TEST_DESIGN.md` and
`patches/phase4/ci_test_proposal/hiprtc_selfcontained.cpp`.

The ordered series also applies cleanly on current develop
(`18e1985`, +37 commits, zero drift in all affected files — Gate P42).

---

**Summary**

Runtime-compiled (HIPRTC) MIOpen kernels currently require a reachable
C++ standard library on HIP >= 7: `miopen_type_traits.hpp` (since #3803)
and `miopen_utility.hpp` (since #3147) disable the internal no-STL
compatibility shims for `HIP_PACKAGE_VERSION_FLAT >= 7000000000` and
unconditionally include the real headers; `radix.hpp` (`<limits>`) and
`tensor_view.hpp` (`<initializer_list>`) include host headers
unconditionally in all versions. On AMD's Windows pip wheels the bundled
msvc-triple clang/hiprtc ships no C++ stdlib and no include-path
configuration, so every runtime-compiled kernel compile fails
(`fatal error: 'type_traits' file not found` →
`HIPRTC_ERROR_COMPILATION`), which PyTorch surfaces as
`miopenStatusUnknownError` (issue #3956; also seen in AMD's own Windows
release-wheel CI, TheRock#8292).

This change restores kernel-source self-containment WITHOUT changing
STL-present behavior: when a real std header is reachable
(`__has_include`), it is used exactly as today; when it is not, new
self-tested freestanding headers provide the required subset. The HIP < 7
legacy shim arms are left unchanged. Deliberately partial standard
libraries (one header reachable, another not) are rejected loudly
(`#error`) instead of risking redefinitions — the #7718 failure class
cannot recur silently.

**Why the HIP >= 7 gate exposed the defect**

The internal no-STL shims predate HIP 7; #3803/#3147 wrapped them in
version gates so modern toolchains would use the real headers. That is
correct for environments that HAVE a host stdlib reachable from hiprtc,
but hiprtc has no requirement that one exists — the Windows wheels are a
shipping counterexample. The gate turned "toolchain quirk" into
"unconditional hard failure" for every runtime-compiled kernel.

**Why this is not an Ultralytics/PyTorch bug**

The failing compile happens inside MIOpen's own RTC path
(`src/comgr.cpp` BuildHip → hiprtc) from kernel sources that MIOpen
embeds; no application-level include configuration can repair it (PyTorch
merely surfaces the error).

**Files changed** (exactly these eight, 5 M + 3 A)

```
projects/miopen/src/kernels/miopen_type_traits.hpp            (probe in HIP>=7 RTC arm)
projects/miopen/src/kernels/miopen_utility.hpp                (same)
projects/miopen/src/kernels/miopen_freestanding_type_traits.hpp   (new)
projects/miopen/src/kernels/miopen_freestanding_utility.hpp       (new)
projects/miopen/src/kernels/miopen_freestanding_initializer_list.hpp (new)
projects/miopen/src/kernels/radix.hpp                          (RTC: builtin limits, no <limits>)
projects/miopen/src/kernels/tensor_view.hpp                    (probe for <initializer_list>)
projects/miopen/src/CMakeLists.txt                             (embed-list registration)
```

**Testing**

- Windows FAIL→PASS on the exact shipped wheel stack (gfx1151, ROCm
  7.14, torch 2.12.0+rocm7.14.0): unpatched MIOpen fails BatchNorm
  training with the field signature; the patched build (Phase 3) and the
  canonical two-commit reconstruction (Phase 4, byte-equivalent, Gate
  P45; rebuilt and loaded with SHA-proven provenance, Gates P50–P51)
  pass BatchNorm train/eval/backward, numerical checks, and YOLO26n
  coco8 1-epoch GPU training — with the machine's MSVC include tree made
  unreachable (no host STL) and re-verified with it present. The 11-op
  non-BN RTC matrix and static 104-entry audit were validated in
  Phase 3 against the byte-identical patched sources and carried over
  via the P45 equivalence.
- Linux PASS→PASS on real gfx1151 (independent validator, exact same
  source SHA + patch bytes): source-built A/B, BN 8/8 → 8/8, non-BN RTC
  11/11 → 11/11, numerics bit-identical (max_abs 0.0 across 37 tensors),
  YOLO predict+train, and actual kthvalue runtime A/B with correct
  values and indices.
- New CI regression test (compile-only, no GPU): compiles the originally
  failing kernel through hiprtc with the host STL isolated; unpatched
  fails with the exact signature, patched produces a code object; strict
  positive/negative controls with an STL-unreachable probe; adversarially
  reviewed against false verdicts (Gate P49).
- Static audit of all 104 RTC kernel entries × std usage committed as a
  reusable script (`scripts/phase3/audit_rtc_std_dependencies.py`).

**Risk**

- Whole-STL-present environments (all of Linux, Windows+MSVC): the probe
  takes the real-STL branch — behavior identical to develop; HIP<7 RTC
  arms untouched; offline builds untouched.
- The freestanding arm only executes where compilation previously always
  failed (strictly better).
- Requires `__has_include` in the RTC compiler (standard C++17; no
  supported clang toolchain is known to lack it).
- Probe outcome is machine-state-dependent: identical MIOpen binaries may
  take different arms on different machines; no semantic difference for
  the audited entity set, but kernel-cache provenance differs across STL
  states.

**Cross-architecture coverage** (explicitly scoped limitation)

Runtime evidence covers gfx1151 (Windows + Linux, ROCm 7.14 wheels).
Compile-level reasoning covers the audited 104-entry RTC closure and the
HIP<7 arms. Upstream-CI legs on gfx94x/gfx110x/gfx120x and a 10.x line
remain the appropriate cross-arch validation (a single contributor
machine cannot own AMD's architecture matrix).

**Related issue**: #3956. Related context: #7718, rocRAND PR #8247,
TheRock#8292.

**DCO**: Signed-off-by pending human confirmation before submission; the
provisional local commits carry an explicit DCO-pending marker and no
sign-off (Gate P54 audit: `docs/phase4/AUTHORSHIP_DCO_AUDIT.md`).

---

*Prepared as part of an independent RCA
(AIwork4me/Ultralytics-Windows-ROCm-Training-RCA, Phases 1–4). No
upstream PR, issue, or comment has been created.*
