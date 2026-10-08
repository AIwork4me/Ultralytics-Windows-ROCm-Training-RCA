# CI Regression Test Design (Gates P47–P49)

Date: 2026-10-08.

## Requirement

A CI test that exercises the underlying defect — runtime-compiled MIOpen
kernels are not self-contained when the HIPRTC toolchain cannot reach a
host C++ standard library:

```text
UNPATCHED kernel source + no host STL  → HIPRTC compile FAIL  ('type_traits' file not found)
PATCHED   kernel source + no host STL  → HIPRTC compile PASS  (non-empty code object)
```

Replaces the Phase-3 proposal artifact
(`patches/phase3/proposed_ci_test/hiprtc_selfcontained.cpp`), which had
four documented wiring defects (missing include dir, target-name typo,
unimplemented negative control, monorepo path mismatch). The Phase-3
artifact is preserved untouched; the new artifact is
`patches/phase4/ci_test_proposal/hiprtc_selfcontained.cpp`.

## What the test compiles

The originally failing production kernel,
`projects/miopen/src/kernels/MIOpenBatchNormFwdTrainSpatial.cpp`, whose
include closure pulls `miopen_type_traits.hpp` (and `miopen_utility.hpp`)
through `batchnorm_functions.hpp → configuration.hpp/vector_types.hpp`.
The kernel source is read from a source-tree directory given on the
command line — the same tree upstream CI would check out.

## Faithfulness to production RTC compilation

Options mirror `src/comgr.cpp` `BuildHip` (`-D__HIP_PLATFORM_AMD__=1`,
`-DHIP_PACKAGE_VERSION_FLAT=<n>`, `-DMIOPEN_HIP_RUNTIME_COMPILE`,
`-Wno-cuda-compat`, `-fno-gpu-rdc`, `-O3`, `-std=c++17`) plus the
production define set for this kernel
(`MIOPEN_USE_FP32=1`, `MIOPEN_LAYER_NCHW=1`, `MIO_BN_VARIANT=0`,
`MIO_BN_GRP0=1024`, …) — the exact set validated on Windows in Phase 3
(`scripts/phase3/compile_bn_patched_tree.py`) and cross-checked against
the Linux probes.

Include resolution design: `-I<kernels-src-dir>` for the quoted kernel
includes (validated Phase-3 mechanism). `hiprtcCreateProgram` named-header
arguments are deliberately NOT used as a substitute for an include search
path (they are a virtual header map). The kernels directory contains no
files named like standard library headers, so angle-bracket `<type_traits>`
resolution depends only on the host toolchain environment — which is the
variable under test.

STL isolation: `-nostdinc++` removes exactly the host C++ standard
library search paths while keeping C headers and hiprtc's internally
injected HIP headers. This reproduces the Windows-wheel condition (no
configured stdlib for the msvc-triple clang) even on machines that have a
toolchain STL installed, and avoids the over-broad `-nostdinc` (which also
removes libc headers that production environments do provide).

## Strict controls (defect 3 of the Phase-3 proposal, implemented)

| Mode | What runs | PASS requires |
|---|---|---|
| `--mode=ordinary` | trivial one-line kernel, no MIOpen sources | compile success + code object |
| `--mode=positive` | BN kernel, `-nostdinc++` | compile success + non-empty code object |
| `--mode=negative` | BN kernel, `-nostdinc++` | compile FAIL **and** log contains `file not found` for one of `type_traits`/`utility`/`limits`/`initializer_list` — any other failure is INCONCLUSIVE (exit 4), never a pass |
| `--mode=with-stl` | BN kernel, ambient include env | compile success + code object (where a host STL exists) |

STL-unreachable probe: before isolated-mode verdicts count, the test
compiles a probe TU that `#error`s when `__has_include(<type_traits>)` is
true under the isolated option set. If the stdlib is still reachable the
run is INCONCLUSIVE — this prevents false positive verdicts that would
otherwise pass through the real-header arm (mission rule: do not infer
isolation without probing effective include resolution).

## Engineering requirements coverage

- CLI: `<kernels-src-dir>`; `--arch` (default gfx1151, the validated
  architecture — no hardcoded gfx90a; CI legs override per target);
  `--hip-flat=N` (default derived from `hiprtcVersion()` as
  major·10⁹+minor·10⁶ — order-preserving; exact package value passed by
  CMake wiring when known; values ≥ 7·10⁹ exercise the affected arm, and
  the test prints a note when they do not).
- Every hiprtc call's result is checked; failures are reported with
  `hiprtcGetErrorString`.
- The complete compiler log is captured (success and failure) and printed
  with a clear delimiter.
- Code-object generation is proven by `hiprtcGetCodeSize` AND retrieving
  the bytes with `hiprtcGetCode` (not just a size query).
- Setup errors (bad args, unreadable kernel source, CreateProgram failure)
  exit 2; semantic FAIL exits 1; INCONCLUSIVE exits 4; PASS exits 0.
- `hiprtcDestroyProgram` runs on every exit path (RAII).

## CMake/CTest integration (Gate P48)

Upstream wiring proposal (kept separate from the two validated source
commits; the test source lives as a proposal artifact at
`patches/phase4/ci_test_proposal/hiprtc_selfcontained.cpp` — a third
commit would be cut from it at submission time if maintainers want it
in-tree):

```cmake
# projects/miopen/test/CMakeLists.txt (addition)
if(BUILD_TESTING AND MIOPEN_USE_HIPRTC)
    add_executable(hiprtc_selfcontained hiprtc_selfcontained.cpp)
    target_link_libraries(hiprtc_selfcontained PRIVATE hiprtc::hiprtc)
    # Compile-only: no GPU, no MIOpen runtime linkage required.
    list(GET AMDGPU_TARGETS 0 _hiprtc_selfcontained_arch) # configure-time default
    add_test(NAME hiprtc_selfcontained
             COMMAND hiprtc_selfcontained ${MIOpen_SOURCE_DIR}/src/kernels
                                             --mode=positive
                                             --arch=${_hiprtc_selfcontained_arch})
    set_tests_properties(hiprtc_selfcontained PROPERTIES LABELS "no-stl")
endif()
```

The `--arch` default resolution and the exact hiprtc target name are to
be adapted to the monorepo's hip package exported targets at wiring time;
the negative control is intended for a dedicated CI leg running against a
pristine checkout (upstream CI convention runs regression tests on the
patched tree; the unpatched control belongs to the PR story/validation
harness, e.g. this repository's `scripts/phase4/run_ci_matrix.py`).

Known limitation of log-matching negative controls (adversarial rounds 1–2,
Reviewer B): an attacker who re-adds `#include <type_traits>` to the
kernel (re-creating the genuine defect) gets a GENUINE
field-signature failure, so `--mode=negative` alone cannot distinguish
"defect present" from "defect re-introduced"; the paired
`--mode=positive` leg on the same tree catches that case (exit 1).
Cross-tree integrity cells (negative×patched and positive×unpatched,
both exit 1) are part of the verified control set.

On this Windows machine the standalone build is verified (Gate P49);
in-tree CTest integration is proposed but not claimed as run.

## Windows execution harness (Gate P49)

`scripts/phase4/run_ci_matrix.py` runs the 3×2 matrix with one binary:

```text
              unpatched tree            patched (canonical) tree
ordinary      PASS expected             PASS expected
positive      expected FAIL(signature)  PASS expected
with-stl      PASS where STL available  PASS expected
```

Recorded per run: hiprtc DLL path + SHA256, source SHA, patch id,
architecture, options, include paths, exit code, compiler log, code object
size.
