# PR DRAFT — FINAL (Gate P5-16) — DO NOT SUBMIT WITHOUT HUMAN APPROVAL

Proposed title:

```text
MIOpen: keep runtime-compiled kernels self-contained without host C++ STL
```

Target: ROCm/rocm-libraries `develop` (base `7c58661`, frozen 2026-10-08).
Series: 3 commits, `patches/phase5/canonical/` (P5-CANDIDATE-R1).
Status markers below distinguish `VALIDATED` (Phase-5 candidate, fresh
evidence), `HISTORICAL VALIDATION` (P3/P4 content), `PENDING NEW
VALIDATION` (not yet executed), and `UPSTREAM CI FOLLOW-UP`.

---

## Background & Motivation

Ultralytics v8.4.171 (October 1, 2026) announced official AMD GPU support
for ROCm-based training and MIGraphX inference ([release], [ultralytics#24137]).
Real Windows training on a Radeon 8060S (gfx1151) with the tested
Ultralytics 8.4.174 then hit a blocking MIOpen failure that predates that
announcement (MIOpen#3956): where HIPRTC cannot reach a host C++ standard
library — as on AMD's Windows wheels — runtime-compiled kernels that
include `<type_traits>` fail with `fatal error: 'type_traits' file not
found`, surfacing as `miopenStatusUnknownError`. This series fixes the
root cause inside MIOpen — general-purpose, workload-agnostic — and adds
a compile-only CI regression test, with reproducible validation on the
affected hardware.

[release]: https://github.com/ultralytics/ultralytics/releases/tag/v8.4.171
[ultralytics#24137]: https://github.com/ultralytics/ultralytics/pull/24137

## Problem statement

On Windows with AMD's pip-wheel ROCm stack (PyTorch 2.12.0+rocm7.14.0,
MIOpen wheel, HIPRTC 7.14), the first BatchNorm training step fails:
HIPRTC compiles `MIOpenBatchNormFwdTrainSpatial.cpp` with the msvc-triple
clang that ships no C++ stdlib and no include-path configuration, so any
kernel-source include of `<type_traits>`/`<utility>`/`<limits>`/
`<initializer_list>` is unresolvable at runtime-compile time. The same
class of failure appears in AMD's own Windows release CI (TheRock#8292)
and has been tracked since HIP 7.0 reworked the shim gates
(MIOpen#3956, rocm-libraries#7718).

## Minimal reproducer (5 lines, PyTorch)

```python
import torch, torch.nn as nn
m = nn.BatchNorm2d(8).cuda().train()          # first RTC kernel compile
y = m(torch.randn(4, 8, 32, 32, device="cuda"))
# unpatched Windows wheel: RuntimeError ... miopenStatusUnknownError
```

## Exact error

```text
fatal error: 'type_traits' file not found
```

(hiprtcCompileProgram log; single diagnostic; reproduces with the
unpatched tree and the STL isolated — see the CI test's negative mode.)

## Root cause and HIP >= 7 history

- `#3803` ("All 7.0 hipRTC fixes") wrapped `miopen_type_traits.hpp` in a
  HIP-version gate; `#3147` independently wrapped `miopen_utility.hpp`.
  Both internal no-STL compatibility shims are therefore disabled for
  HIP >= 7, and the real `<type_traits>`/`<utility>` headers are included
  even in runtime-compile mode.
- That is correct where a host stdlib resolves, but on HIPRTC toolchains
  without one (Windows wheels), compilation now fails outright instead
  of falling back.

## Why this belongs in MIOpen

The defect is MIOpen's runtime-compile path requiring a host C++
standard library that HIPRTC does not guarantee. Every consumer of
MIOpen's wheel (or any no-stdlib HIPRTC environment) hits it regardless
of framework; patching consumers would duplicate an STL workaround per
workload.

## Selected design: `__has_include` availability probe

Prefer the real standard headers whenever they are reachable
(`__has_include`), so STL-present environments keep byte-identical
behavior; fall back to new freestanding definitions only where no
standard library resolves — the state in which compilation previously
always failed. Deliberately partial standard libraries (one header
reachable, the other not) are rejected with a loud `#error` instead of
risking redefinitions.

## Freestanding-header behavior

Three small MIT-licensed headers (`miopen_freestanding_type_traits.hpp`,
`miopen_freestanding_utility.hpp`,
`miopen_freestanding_initializer_list.hpp`) provide `std::`-namespace
definitions the kernel sources name, active only in runtime-compile mode
with no reachable stdlib. Every trait carries a `static_assert`
self-test, so any compile of the headers verifies its own correctness.
`radix.hpp`'s `std::numeric_limits` uses become `__INT32_MAX__`/
`__INT64_MAX__` (unconditionally — values identical), and the offline
path keeps `<limits>` for transitive users.

## Partial-STL safeguards

`miopen_type_traits.hpp` / `miopen_utility.hpp` cross-probe
`<type_traits>` and `<utility>`; if exactly one is reachable the compile
fails with an explicit inconsistent-availability `#error` rather than
silently mixing definitions.

## HIP < 7 and offline paths remain compatible

Legacy shim arms below HIP 7 are untouched. Offline (`hipcc`) builds
include the real headers exactly as before; `radix.hpp` keeps
`<limits>` offline. Linux source builds: unpatched PASS / patched PASS
(HISTORICAL VALIDATION, P3 content).

## Evidence

| Claim | Status | Where |
|---|---|---|
| Windows patched PASS: BN train, no-STL runtime, numerics vs CPU, YOLO26n coco8 1-epoch (amp=False AND default AMP with "AMP: checks passed"), DLL provenance per run | VALIDATED (Phase-5 candidate, gfx1151, ROCm 7.14) | `evidence/phase5/runtime/`, `evidence/phase5/yolo/` |
| Windows unpatched FAIL: compile-level A/B (exact `'type_traits' file not found` signature, sole error) in the CI matrix; the runtime traceback (`miopenStatusUnknownError`) is documented in MIOpen#3956 and the Phase-3/4 runtime logs | VALIDATED (compile-level) + issue-documented (runtime) | `evidence/phase5/ci/ci_matrix_phase5.json`, MIOpen#3956 |
| Windows same-matrix PASS on the P3 content (incl. DLL provenance GetModuleFileNameW+SHA256) | HISTORICAL VALIDATION | `evidence/phase4/` |
| Linux source-built unpatched PASS / patched PASS; numerics bit-identical; kthvalue PASS→PASS | HISTORICAL VALIDATION (P3 content) | `rca/linux-gfx1151-phase3-regression` branch |
| Phase-5 candidate on Linux | PENDING NEW VALIDATION | `docs/phase5/LINUX_FINAL_VALIDATION_HANDOFF.md` |
| CI test in-tree CTest: configure/build/discover/run | VALIDATED | `evidence/phase5/ci/` |
| CI A/B matrix incl. adversarial cells | VALIDATED 13/13 | `evidence/phase5/ci/ci_matrix_phase5.json` |

(Phase-5 Windows validation enumerated in the maintainer report; nothing
is claimed PASS without logged evidence.)

## Commit series

1. `MIOpen: keep RTC type traits self-contained when no host STL is reachable`
2. `MIOpen: make remaining RTC kernel std includes self-contained`
3. `MIOpen: add HIPRTC no-host-STL regression test`

## CI regression test

Compile-only, no GPU required; compiles the real
`MIOpenBatchNormFwdTrainSpatial.cpp` through hiprtc with the host STL
unreachable and requires a non-empty code object; registered in
`test/CMakeLists.txt` under `MIOPEN_USE_HIPRTC` with configure-time arch
selection; negative control deliberately not in the default suite.
CTest: discovery + execution PASS on Windows (gfx1151); the same matrix
passed on the standalone harness (6/6) in Phase 4.

## Remaining scope

- Cross-architecture compile-only legs (gfx94x/gfx110x/gfx120x + one
  10.x line) — UPSTREAM CI FOLLOW-UP (arch is a `--arch`/CMake override).
- Linux targeted revalidation of this exact candidate — PENDING NEW
  VALIDATION (handoff ready).
- Kthvalue runtime evidence: HISTORICAL VALIDATION (P3, Linux);
  Phase-5 Windows YOLO train covers radix consumers end-to-end.

## Associated issue

MIOpen#3956 (context: rocm-libraries#7718, TheRock#8292).

---

Reviewer guidance: two reviewers per `projects/miopen/CONTRIBUTING.md`;
author happy to run any additional leg on the Radeon 8060S machine.
