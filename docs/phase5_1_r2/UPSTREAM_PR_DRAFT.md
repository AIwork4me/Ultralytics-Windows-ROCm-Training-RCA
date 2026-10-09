# UPSTREAM PR DRAFT — LOCAL DRAFT ONLY (do NOT submit without human authorization)

Title: `MIOpen: keep RTC kernels self-contained when no host STL is reachable (+ portable HIPRTC regression test)`

## Problem

On Windows ROCm (HIPRTC) environments, MIOpen's runtime-compiled kernels
fail to build: the kernel sources include standard C++ headers
(`<type_traits>`, `<utility>`, `<limits>`, `<initializer_list>` …) that
are reachable through the ordinary host compiler but NOT through the
HIPRTC compilation environment, which has no host C++ standard library
on the search path (issue #3956 field signature:
`fatal error: 'type_traits' file not found`). Training workloads die at
the first BatchNorm RTC compile.

## Root cause

Runtime-compiled (`MIOPEN_USE_HIPRTC`) kernel include chains depend on
host STL headers that are not guaranteed to exist in the HIPRTC
environment. The kernels' own logic needs only a handful of traits/
utilities, so the dependency is incidental, not fundamental.

## Solution

Make the affected include paths self-contained:
1. `miopen_type_traits.hpp` gates its `<type_traits>` use behind
   `__has_include` and falls back to a new freestanding implementation
   (`miopen_freestanding_type_traits.hpp`) when the header is absent.
2. The remaining kernel std includes (`radix.hpp`, `tensor_view.hpp`) get
   the same treatment via `miopen_freestanding_utility.hpp` /
   `miopen_freestanding_initializer_list.hpp`. No algorithm changes; the
   production kernels' compiled behavior is unchanged (validated
   numerically).

## Regression test

`test_hiprtc_selfcontained` — a compile-only CTest that drives hiprtc
exactly like MIOpen's runtime-compile path (no MIOpen in the process) and
compiles the real `MIOpenBatchNormFwdTrainSpatial.cpp` with the host C++
STL unreachable; it passes only if the include closure is self-contained
and a non-empty code object is produced. Portability design:

- Links whichever hiprtc target the package exports (`hiprtc::hiprtc`
  imported target when present, plain `hiprtc` otherwise) — the Linux
  package exports only the namespaced target, whose usage requirements
  the test needs since it deliberately links nothing else.
- Registered via a direct `add_test` applying the same SKIP_TESTS /
  SKIP_ALL_EXCEPT_TESTS policy as `add_test_command`, bypassing its
  MIOPEN_TEST_GDB wrapper (non-WIN32 default), which folds every nonzero
  exit into a generic failure — the test's own exit code is the verdict.
- `SKIP_RETURN_CODE 4`: the test verifies its own STL-unreachability
  before issuing a verdict; on hosts that cannot reproduce the no-STL
  condition (e.g. Linux ROCm ≥7.x where libhiprtc-builtins embeds the
  headers), it exits 4 and CTest records Skipped instead of failing the
  leg — an honest INCONCLUSIVE, never a PASS. Exit 0 = PASS, 1 = FAIL
  (a genuinely broken tree still fails hard on isolating hosts).
- The hiprtc runtime directory (DLL beside the import library's package
  root on Windows) is derived from the imported target's location
  metadata and exposed to the test alone, so a bare `ctest` run works
  without machine-wide PATH setup.

## Platform behavior

- Windows (gfx1151, ROCm 7.14 wheels): real no-STL positive PASS
  (probe-verified isolation, 5784-byte code object); full adversarial
  matrix 13/13 including unpatched-tree exact-signature failure and
  STL-reachability (exit 4) cells.
- Linux (ROCm 7.14.1, gfx1100): full host-STL isolation is not
  reproducible (headers embedded in libhiprtc-builtins under every
  isolation flag) — the test reports Skipped; `--mode=ordinary` and
  `--mode=with-stl` controls PASS. (Independent Linux A/B validation of
  the kernel fix itself is in progress; not claimed here.)

## Real-workload evidence

Windows: BatchNorm forward/backward vs CPU fp64 within 1e-5-class
tolerances; fresh-cache no-STL training workload; YOLO26n coco8 1-epoch
training PASS (amp=False and default AMP). Full hashes/logs in the
evidence repository (link below).

## Evidence

Reproducible artifacts (patches with SHA256, commit/tree identities,
CTest logs, adversarial matrix, numerics, training logs, DLL provenance):
`https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA`
→ `patches/phase5_1_r2/canonical/`, `docs/phase5_1_r2/`,
`evidence/phase5_1_r2/`, manifest `findings/phase5_1_r2/FINAL_HANDOFF.json`
(series sha256_file_concat_v1
`4a703d69cc3e111408fad593761a3f017619ced4cf007f0f565ca98472c91bcf`).

## Limitations (explicit)

- This fixes the RTC self-containment defect for the affected include
  paths; it does not claim to resolve every Windows ROCm training failure.
- On non-isolating hosts the regression test self-skips (visible, not
  counted as pass); Windows isolating hosts get the hard verdict.
- Linux final A/B validation PENDING at draft time (honest status; update
  before submission).
- Commits are not DCO-signed: upstream CONTRIBUTING.md (inspected at the
  proposed base) states no DCO requirement. If maintainers require
  sign-off, it will be provided on request.
