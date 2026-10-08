# Maintainer Report — FINAL (Gate P55)

**Subject**: MIOpen RTC kernels must stay self-contained without a host
C++ standard library (fix for the Windows-wheel / no-STL compile failure)

**Series**: two commits on `b68f894` (develop, 2026-10-07), byte-equivalent
to the cross-platform-validated patch series P3-FINAL-R3; applies cleanly
on current develop `18e1985` (+37 commits, no affected-file drift).

**Provisional status**: DCO pending human confirmation; no upstream
action taken.

---

## 1. Problem and minimal reproducer

On hosts where the hiprtc toolchain cannot resolve a host C++ standard
library, EVERY runtime-compiled MIOpen kernel fails:

```text
MIOpenBatchNormFwdTrainSpatial.cpp
 → batchnorm_functions.hpp → configuration.hpp/vector_types.hpp
 → miopen_type_traits.hpp:151:10:
   fatal error: 'type_traits' file not found
 → HIPRTC_ERROR_COMPILATION → miopenStatusUnknownError
```

Minimal reproducer (no PyTorch needed): compile the kernel through
hiprtc with the host STL unreachable — e.g. `hiprtc_selfcontained`
(`patches/phase4/ci_test_proposal/`), `--mode=negative` on develop and
`--mode=positive` with this series. Affected environments include AMD's
Windows pip wheels (msvc-triple clang, no stdlib, no include config) —
MIOpen#3956 — and AMD's own Windows release-wheel CI (TheRock#8292).

## 2. Root cause

`miopen_type_traits.hpp` (PR #3803) and `miopen_utility.hpp` (PR #3147)
gate the built-in no-STL `namespace std` shims to
`HIP_PACKAGE_VERSION_FLAT < 7000000000`, so HIP >= 7 runtime-compiled
kernels include the real headers unconditionally. `radix.hpp`
(`<limits>`) and `tensor_view.hpp` (`<initializer_list>`) were never
guarded at all. Nothing in the RTC contract guarantees a host stdlib is
reachable.

## 3. Why the HIP >= 7 gate exposed the defect

The shims existed precisely for stdlib-less toolchains; the version gate
assumed "modern HIP ⟹ real headers available". That holds for typical
Linux CI, not for the Windows wheel toolchain, turning a compat path
into an unconditional hard failure.

## 4. Why this is not an Ultralytics bug

The failure is entirely inside MIOpen's RTC path
(`src/comgr.cpp` → hiprtc) on kernel sources MIOpen embeds; the
application (Ultralytics/PyTorch) only surfaces `miopenStatusUnknownError`
from `torch.nn.BatchNorm2d(...)` in training mode.

## 5. The `__has_include` strategy

Within the HIP>=7 RTC arm only: prefer the real header when reachable —
STL-present environments keep today's behavior exactly (same headers,
same content) — else fall back to freestanding definitions. Search-path
existence (`__has_include`) is TU-global, so the selection cannot mix.
Deliberately partial stdlibs (e.g. `<utility>` reachable but
`<type_traits>` not) `#error` loudly — no silent redefinition risk with
`__has_include`-selected real headers (contrast the historical #7718
macro-based class of failure).

## 6. Freestanding fallbacks

Three new headers (`miopen_freestanding_{type_traits,utility,
initializer_list}.hpp`) provide the exact entity set the audited RTC
kernel closure uses (104-entry audit; script included): type traits
(remove_reference/const/volatile/cv, integral_constant, true/false_type,
is_same, is_pointer, enable_if, conditional), utility (move/forward/
exchange/pair-piecewise), initializer_list lowered via clang builtins
(`__builtin_...`) for older wheel clangs. Each carries static_assert
self-tests; runtime canaries executed on gfx1151 verify every facility.

## 7. Partial-STL detection behavior

Inconsistent availability is a hard `#error` at compile time (loud,
actionable) rather than an ODR/ODR-like hazard.

## 8. Compatibility

- HIP < 7: all legacy arms unchanged (bytes preserved).
- Offline (comgr/aot) builds: unchanged — probes live only in the
  RTC-compile arms; offline compilers with full STL take the real-header
  branch identical to develop.
- STL-present hosts: identical to develop (Linux-validated bit-identical
  numerics).

## 9–12. Evidence (Windows FAIL→PASS; Linux PASS→PASS; bit-identical
numerics; kthvalue runtime)

- **Windows** (gfx1151, ROCm 7.14.0 wheels, torch 2.12.0+rocm7.14.0):
  - Unpatched wheel MIOpen: BatchNorm train FAIL (field signature).
  - Phase-3 patched build: BatchNorm matrix + 5 controls, numerics
    ≤ 9.5e-7 vs CPU; 11-op non-BN RTC matrix; YOLO26n coco8 1-epoch
    train (both amp modes); with MSVC include tree unreachable and
    re-verified restored.
  - **Phase 4 canonical reconstruction**: 8/8 byte-equivalence (P45,
    independently reconstructed), fresh rebuild of MIOpen.dll from the
    two commits (P50), SHA-proven load by PyTorch (P51), BatchNorm +
    numerics + YOLO train rerun (P52) — see evidence/phase4/.
- **Linux** (independent validator, gfx1151, same SHA + patch bytes):
  source-built A/B; BN 8/8→8/8; non-BN 11/11→11/11; numerics
  **bit-identical (max_abs 0.0, 37 tensors, CPU-referenced)**; YOLO
  predict+train; **kthvalue runtime unpatched PASS → patched PASS**
  (values+indices byte-identical A/B; adversarial falsification review).

## 13. Regression test and CI integration

Compile-only `hiprtc_selfcontained` test (no GPU required): strict
positive/negative controls with exact field-signature matching, single-
error requirement, mandatory STL-unreachable probe, full log capture,
RAII resource release, meaningful exit codes. Validated 6/6 matrix
(ordinary/positive/negative/with-stl × unpatched/patched) on the real
trees; hardened after an adversarial review that had found four
false-verdict vectors (all now rejected as INCONCLUSIVE/usage-error).
CMake wiring proposal included (`BUILD_TESTING` + `MIOPEN_USE_HIPRTC`
gated).

## 14. Remaining cross-architecture coverage

Runtime: gfx1151 only (Windows + Linux, ROCm 7.14). Upstream CI should
add compile-only no-STL legs for gfx94x/110x/120x and a 10.x line
(gate logic verified present on 10.x source in Phase 3 review; new arm
exercised).

## 15. Related upstream issues

MIOpen#3956 (this defect, open); MIOpen#7718 (historic double-definition
class — motivation for loud partial-STL rejection); rocRAND PR #8247
(rocRAND counterpart fix); TheRock#8292 (same signature in AMD's Windows
release CI).

## Submission hygiene

- Two-commit series, small and independently meaningful; canonical
  format-patch output archived; `git am` round-trip verified.
- Author/DCO: provisional only (no sign-off; explicit pending marker);
  MIT attribution placeholder in the three new headers per maintainer
  preference — both flagged for the human submitter.
- clang-format: repo style not enforced on these kernels today (2 of 4
  modified files violate `.clang-format` at the validated baseline);
  no reformat applied to preserve byte-equivalence — noted as a possible
  reviewer request requiring a follow-up candidate.
