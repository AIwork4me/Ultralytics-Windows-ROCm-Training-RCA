# GTest Architecture Comparison — HIPRTC no-host-STL regression (PR #13437, review thread 4)

Date: 2026-10-12 · Worktree: `rocm-libraries-phase5.5-submission` @ `review-r1/gtest-design` (3c8e5ffe)
Reviewer request (comment 4247502213): *"Please use the existing runtime-compilation test
infrastructure, e.g. gtests like `gtest/handle_test.cpp` or `gtest/miopen_cstdint_lp64.cpp`,
instead of a standalone hipRTC test."*

## What the test must guarantee (from the field failure, MIOpen#3956)

1. Real Windows no-host-STL isolation **proven** (probe: STL unreachable under the isolation flag).
2. The **actual** `MIOpenBatchNormFwdTrainSpatial.cpp` kernel source compiled (identity-guarded, not a substitute).
3. Positive control passes **with a materialized, non-empty code object**.
4. Unpatched-tree negative control reproduces the exact field diagnostic
   (`fatal error: 'type_traits' file not found`, sole error) — and nothing else counts.
5. Ordinary toolchain control passes.
6. With-STL control passes where an ambient STL exists.
7. Hosts that cannot reproduce the no-STL condition report **Skipped**, never Passed.
8. Setup/compile failures can never become a pass.
9. Correct HIPRTC runtime provenance (the DLL the test drives is the package's hiprtc).
10. Existing Linux behavior (honest skip on stock toolchains) unchanged.

## Option A — `Handle::AddKernel` + MIOpen runtime-compilation infrastructure

Model: `gtest/miopen_cstdint_lp64.cpp` — inline kernel source through the real comgr/hipRTC path.

Source analysis (`src/hip/handlehip.cpp:555`, `src/hipoc/hipoc_program.cpp:186`, `src/comgr.cpp:788`):

- `AddKernel(..., params, ...)` `params` flow into `hiprtc::BuildHip` after space-splitting; the
  hipRTC-side option filter (`comgr.cpp:563`) removes only `-mcpu=*`, so an isolation flag such as
  `-nostdinc` **does** survive. Isolation via `params` is technically possible.
- `BuildHip` appends its own production options (`-DMIOPEN_HIP_RUNTIME_COMPILE`, `-O3`,
  `-std=c++17`, and `-I$ROCM_PATH/include` when `ROCM_PATH` is set) and injects every kernel
  header as hiprtc **named headers** (`comgr.cpp:698`) — this is the true field path, so option
  fidelity is maximal.
- **Failure semantics break guarantee 4**: a compile failure throws the generic
  `Code object build failed. Source: <name>` (`hipoc_program.cpp:204`); the clang log — the only
  place the exact `'type_traits' file not found` signature lives — goes to the MIOpen logger, not
  the exception. In-process stderr capture would be required to keep the signature check, which
  is fragile and not something the repo does today.
- **GPU required** (`get_handle()` initializes a device): the test stops being compile-only and
  disappears from no-GPU legs.
- Probe semantics: the `__has_include` + `#error` probe would have to be detected through
  exception-vs-success, losing the log-level evidence.

## Option B — existing gtest registration + direct hipRTC (chosen)

The test becomes a normal gtest in `test/gtest/` (glob-registered naming, `check_names.py`
schema, `gtest_discover_tests` PRE_TEST discovery, standard `MIOPEN_GTEST_FILTER` selection),
but keeps direct hipRTC calls to own the include environment.

Registration (`test/gtest/CMakeLists.txt`): the file is removed from the auto-glob and
registered by an explicit block, because

- `add_gtest()` links `miopen_gtest_common`/`MIOpen_with_plugins` but MIOpen links hiprtc
  **PRIVATE** (`src/CMakeLists.txt:1096`), so hiprtc symbols do not propagate — a direct-hipRTC
  test must add `hiprtc::hiprtc` itself;
- the standard monolith path (`miopen_gtest`) has the same gap;
- the old standalone needed the same custom registration anyway — the redesign keeps exactly one
  custom block, now inside the standard gtest directory with standard discovery/filtering.

Windows hiprtc.dll provenance is preserved by deriving the runtime directory from the imported
hiprtc target's location metadata and prepending it to `PATH` via the ctest `ENVIRONMENT`
(generated discovery file verified to carry it).

Exit-code contract → gtest semantics: hard pass/fail from `ASSERT_*`; `GTEST_SKIP()` for
"host cannot reproduce the no-STL condition" and for the not-enabled negative control.
Verified on CMake 4.4.4 + GTest 1.14.0: ctest reports such tests as
`The following tests did not run: … (Skipped)` — the explicit-skip guarantee holds.
A/B knobs become environment overrides with compiled-in defaults
(`MIOPEN_TEST_HIPRTC_KERNELS_DIR` / `_ARCH` / `_ISOLATE` / `_UNPATCHED_KERNELS_DIR`).

### Prototype / validation results (Windows 11, gfx1151, ROCm 7.14.0 wheel stack)

Fresh configure (`MIOPEN_TEST_ALL=ON`), target build, ctest:

```
1/4 CPU_HiprtcSelfContained_NONE.OrdinaryToolchainControl        Passed  0.34s
2/4 CPU_HiprtcSelfContained_NONE.BatchNormKernelWithoutHostStdlib Passed  0.62s   <- real no-STL PASS
3/4 CPU_HiprtcSelfContained_NONE.BatchNormKernelWithAmbientStdlib Passed  0.40s
4/4 CPU_HiprtcSelfContained_NONE.UnpatchedTreeFailsWithFieldSignature Skipped
```

- Negative control with `MIOPEN_TEST_HIPRTC_UNPATCHED_KERNELS_DIR` → pristine tree @54b079ca:
  `Passed` — log shows `miopen_type_traits.hpp:151:10: fatal error: 'type_traits' file not found`,
  `1 error generated`, i.e. the exact field signature as the sole error.
- Ineffective isolation (`MIOPEN_TEST_HIPRTC_ISOLATE=-Wno-unused`) → `Skipped`
  ("host C++ stdlib still reachable") — never a silent pass.
- `check_names.py` exit 0; no duplicate registration (`ctest -N`: exactly 4 hiprtc tests, 309 total).
- Adversarial A/B matrix, 13/13 PASS (see `review_r1_build/evidence/r1_adversarial_matrix.json`),
  including `positive/unpatched` → FAILED, `negative/patched` → FAILED (rejects the expectation),
  missing/wrong kernels dir → FAILED, bad arch → FAILED, CPATH leak → Skipped, and
  substituted-kernel-source → FAILED (hardened beyond the standalone: the source must include a
  real closure header, e.g. `configuration.hpp`, not just carry identity strings).

## Portability assessment

- **Linux**: identical machinery; stock toolchains (libhiprtc-builtins embedding C++ headers)
  keep the STL reachable under `-nostdinc` → `GTEST_SKIP` — same honest outcome as the
  standalone's exit-4/CTest-Skipped. GNU-triple hosts may set
  `MIOPEN_TEST_HIPRTC_ISOLATE=-nostdinc++` if they want libc headers visible; the probe still
  governs whether verdicts count.
- **Windows**: proven above; the ctest `ENVIRONMENT` PATH entry reproduces the old registration's
  DLL-provenance handling; the process links only GTest + hiprtc (no MIOpen, no HIP runtime),
  so no GPU and no MIOpen DLL graph is required to run it.
- **No-GPU legs**: test is compile-only and CPU-named, so it stays available where `*GPU*` tests
  are filtered out.
- **Smoke-mode builds** (`MIOPEN_TEST_ALL=OFF`): the standard filter (`Smoke*NONE*`) selects
  nothing — identical to the maintainer-cited `miopen_cstdint_lp64.cpp` behavior; full-tier legs
  (`MIOPEN_TEST_ALL=ON`) register the suite. Wiring into specific CI tiers follows whatever
  selection `miopen_cstdint_lp64.cpp` gets.

## CI integration assessment

- Standard `gtest_discover_tests` PRE_TEST discovery; failure to load the binary at discovery is
  a loud error, not a pass.
- Standard ENVIRONMENT properties (incl. the Windows PATH entry) are carried into the discovery
  and run phases (verified in the generated `_discovery.cmake`).
- No new CMake dependencies beyond what the standalone already used (GTest + hiprtc).

## Coverage preserved / lost vs the standalone test

Preserved (all 10 guarantees; see validation above), with two improvements:
substituted-source detection is stronger, and the negative control is now always-visible
(skipped) rather than an out-of-tree invocation only.

Lost: none functionally. The standalone's CLI `--mode`/`--arch`/`--hip-flat` flags become env
overrides; `--hip-flat` derivation from `hiprtcVersion()` is unchanged (CI wiring that knows the
exact package value can no longer override it — if a leg ever needs that, an env knob is a
one-line addition).

## Recommendation

**Option B**: a real gtest in `test/gtest/hiprtc_selfcontained.cpp` (suite
`CPU_HiprtcSelfContained_NONE`) that drives hipRTC directly, registered through the standard
gtest discovery with one explicit CMake block that links GTest + hiprtc only.

The primary reason is the **compile-only / no-GPU property**: the regression is a property of the
hipRTC include environment, so the test owns its options and runs on hosts without a GPU or a
functional MIOpen runtime. The secondary reason is the exact-diagnostic negative control: routing
through `Handle::AddKernel` surfaces compile failures only as the generic
`Code object build failed` exception (`comgr.cpp` logs the clang diagnostic but does not
propagate it), which the unpatched-tree A/B control needs. Note the CI-runnable controls
(positive/ordinary/with-STL) *could* be expressed via AddKernel (`params` survives option
filtering) at the cost of the GPU requirement; only the signature A/B genuinely needs raw log
access. Option B also compiles the kernel via `-I` filesystem resolution rather than comgr's
named-header injection — equivalent for the property under test (header closure + host STL
reachability), but a fidelity difference worth stating.

Known gaps deliberately left to maintainer direction (asked, not assumed):
- **Tier labels**: `apply_test_category_labels` runs only on the `miopen_gtest` monolith target,
  so this discrete registration carries no `quick/standard/full` labels and is not in
  `test_categories.yaml`; which legs should run it is an open question (stock Linux legs will
  honestly skip 2–3 of the 4 tests; the host class that exercises the regression is a
  Windows pip-wheel-style toolchain).
- **check_names.py** enforcement is monolith-based too; the suite name was validated manually
  against the schema (exit 0) but is not covered by the monolith's automated check.
- The custom registration duplicates the SKIP_TESTS/Smoke-prefix selection policy that
  `add_gtest` owns; factoring that into a shared helper is a possible follow-up if the
  maintainer prefers.

Option A was rejected because it drops the compile-only/no-GPU property outright and loses the
exact-diagnostic control. Option C (standalone) is what the reviewer asked to replace.
