# UPSTREAM PR DRAFT — FINAL (Gate P54-08)

> Target repository: `ROCm/rocm-libraries` (branch off `develop`). NOT submitted — awaiting explicit human authorization. Commits unsigned (no DCO requirement found in the project's contribution guide).

---

**Title:** `MIOpen: make HIPRTC kernel includes self-contained without host STL`

## Problem

On Windows runtime-only ROCm installs (e.g. the PyTorch pip wheels, which depend on `hip-runtime-amd` but not `hip-dev`/MSVC), MIOpen's runtime-compiled kernels fail to build because kernel headers include host C++ standard-library headers that hipRTC cannot resolve. User-visible failure (`ROCm/MIOpen#3956`, Radeon RX 9060 XT / gfx1200, ROCm 7.2.1, Windows 11):

```
MIOpen(HIP): Error [BuildHip] HIPRTC status = HIPRTC_ERROR_COMPILATION (6),
  source file: MIOpenBatchNormFwdTrainSpatialHIP.cpp
... include\miopen_type_traits.hpp:151:10: fatal error: 'type_traits' file not found
RuntimeError: miopenStatusUnknownError
```

i.e. `nn.BatchNorm2d` (and any other op whose kernel is JIT-compiled at runtime) breaks on a machine that has no host C++ standard library reachable from the RTC include path. The same class has been observed in AMD's own Windows release CI (TheRock#8292).

## Root Cause

Since the HIP 7.0 hipRTC rework (MIOpen#3803), runtime-compiled kernels reach for the *real* host standard headers (`<type_traits>`, `<utility>`, `<limits>`, `<initializer_list>`) unconditionally in the `HIP_PACKAGE_VERSION_FLAT >= 7` RTC quadrant. hipRTC's include environment, however, only guarantees the HIP/ROCm headers — whether a host C++ standard library resolves is a property of the *installation*, not of the compiler. Runtime-only installs have none, so any kernel whose include closure touches those headers fails to JIT.

## Changes

Three commits, ten files (6 modified, 4 added):

1. **`keep RTC type traits self-contained when no host STL is reachable`** — `miopen_type_traits.hpp`/`miopen_utility.hpp` select the real `<type_traits>`/`<utility>` via `__has_include` when reachable (unchanged behavior for ordinary installs), and fall back to new freestanding drop-ins otherwise. New files `miopen_freestanding_type_traits.hpp` (traits + per-trait `static_assert` self-tests) and `miopen_freestanding_utility.hpp` (`std::forward`). Partial-STL inconsistencies become loud `#error`s. Only the (RTC ∧ HIP ≥ 7) quadrant changes; HIP < 7 and non-RTC builds are byte-equivalent.
2. **`make remaining RTC kernel std includes self-contained`** — `radix.hpp`'s *include* switches to `miopen_cstdint.hpp` in RTC mode, and its `numeric_limits<int32_t/int64_t>::max()` tokens become `__INT32_MAX__`/`__INT64_MAX__` (definitionally the same values; the substitution is unconditional, not runtime-compile-only — offline builds change tokens too); `tensor_view.hpp` falls back to a new freestanding `initializer_list` (clang's exact two-field lowering, `__clang__`-guarded); the three new headers are added to the kernel shipping list. The freestanding definitions live in separate new files rather than being inlined into the selectors (as the legacy HIP<7 arm does) because each fallback needs its own misuse `#error` guard and self-tests, the initializer_list one is clang-only, and the 1:1 selector↔fallback↔std-header mapping keeps the partial-STL cross-checks local — the same choice upstream made for `miopen_cstdint.hpp` (#12623). Note: the `tensor_view.hpp` reachability probe is deliberately not HIP-version-gated, so it also repairs the HIP<7+RTC+no-STL configuration (previously always failed); no configuration that previously compiled changes behavior.
3. **`add portable HIPRTC no-host-STL regression test`** — `test/hiprtc_selfcontained.cpp` + CTest registration: compiles the real `MIOpenBatchNormFwdTrainSpatial.cpp` through hipRTC with the host STL unreachable; passes only when the include closure stays self-contained and a code object is produced. Built-in hardening: substituted/truncated kernel detection, an isolation probe, and a negative mode requiring the exact `'type_traits' file not found` signature as the sole error. Hosts that cannot reproduce the no-STL condition report skip (exit 4), never pass.

## Reproduction

```bash
# Windows, PyTorch ROCm wheel env (no MSVC include path):
python -c "import torch.nn as nn; m=nn.BatchNorm2d(100).cuda(); import torch; print(m(torch.randn(20,100,35,45,device='cuda')).shape)"
# unpatched: miopenStatusUnknownError + "fatal error: 'type_traits' file not found"

# Regression test (in-tree, after this PR):
cmake -S projects/miopen -B build -DBUILD_TESTING=ON -DMIOPEN_USE_HIPRTC=ON ...
cmake --build build --target test_hiprtc_selfcontained
ctest --test-dir build -R test_hiprtc_selfcontained   # Windows: Passed; Linux stock toolchain: Skipped (see below)
```

Full RCA with frozen evidence, A/B numerics, and per-gate reproducible logs: see Evidence links below.

## Validation

| Platform | GPU / toolchain | Result |
|---|---|---|
| Windows 11 | Radeon 8060S (gfx1151), ROCm 7.14.0 wheel, hipRTC 7.14 | no-STL regression test **Passed** (genuine, not skipped); 13/13 adversarial matrix incl. unpatched-control reproducing the exact field signature; bare-environment CTest pass (no ambient ROCm PATH); BF16 restricted-leg skip parity; fresh-build MIOpen.dll (`44d43887…`) in-process provenance, BatchNorm fwd/bwd numerics identical to the frozen R2 values and within pre-registered tolerances; no-STL runtime scenario PASS; YOLO26n coco8 1-epoch smoke PASS (`amp=False` **and** default-AMP — genuine AMP this run, see Known Limitations); wheel restored and verified |
| Linux (Ubuntu 24.04) | Radeon PRO W7900 (gfx1100), ROCm 7.14.1 | source A/B (unpatched vs patched libMIOpen): kthvalue 3/3 byte-identical dumps, BatchNorm 6/6 numerics identical, ordinary+with-STL controls PASS; no-STL CTest legitimately **Skipped** (see Regression Test) |
| Linux gfx1151 (8060S) | Phase 5.3B | *pending independent validation* |

Rebased and re-validated on develop as of **2026-10-09 (`681bc9ed`)**: all six modified upstream files were blob-identical to the R2-frozen versions; the three-patch series applies cleanly (`git am`, zero conflicts; independent index reconstruction reproduces the same tree), and the full Windows validation above was re-run on that replay tree. (Develop advanced 3 commits past `681bc9ed` later the same day — all outside `projects/miopen`, ten-file blob audit unchanged — see the RCA branch's develop-drift addendum; submission-day refresh procedure included in the checklist.)

## Regression Test

- **Windows (no-STL capable hosts):** hard requirement — the test compiles the BatchNorm kernel under a verified-unreachable host STL and must produce a code object. Skip is impossible unless the isolation probe proves the host *cannot* reproduce the no-STL condition.
- **Linux stock toolchains:** `libhiprtc-builtins` embeds the C++ headers, so the isolation probe reports INCONCLUSIVE → CTest shows the run as **Skipped** (exit 4 / `SKIP_RETURN_CODE 4`), never as a pass. The Windows no-STL evidence is the load-bearing proof; Linux still runs the ordinary and with-STL controls. **CI note:** a runner image that exports `CPATH` (conda/LLVM toolchain images) makes the host STL reachable and the test will likewise report Skipped — green but silent. The no-STL CI leg should run without ambient `CPATH` (and may assert the test was not skipped on that leg).
- **Exit-code contract:** 0 pass, 1/2 fail, 4 skip (fixture-verified on both platforms).
- **Define fidelity:** the test's RTC define set exercises the same define *classes* as the production BatchNorm compile (`__HIP_PLATFORM_AMD__`, `MIOPEN_USE_*` variants, `MIO_BN_VARIANT/GRP*`, runtime-queried `HIP_PACKAGE_VERSION_FLAT`, `MIOPEN_HIP_RUNTIME_COMPILE`, `-std=c++17`, arch, kernels-dir include). Production's ~16 per-instance value-defines (`MIO_BN_N`, `MIO_BN_LDS_SIZE`, `MIO_SAVE_MEAN_VARIANCE`, …) are omitted and covered by `default_configurations.hpp` defaults instead — immaterial to include-closure semantics; two legacy layout defines carried by the test have no consumers in-tree.

## Scope

- Fixes the HIPRTC host-header availability failure only. **Not** addressed: unrelated Windows training failures, TheRock gfx1151 CI numerical issues (`rocm-libraries#3956` — different issue, number collision with the MIOpen issue of the same number), BF16 preamble type availability (PR #12733, disjoint files).
- The default-suite test exercises the BatchNorm kernel's closure; the other self-containment sites (`radix.hpp`, `tensor_view.hpp` consumers) are covered by the A/B validation harnesses linked below rather than by this default test — kept minimal deliberately.

## Known Limitations

- Linux no-STL isolation depends on the toolchain; where unavailable the new test skips (by design, honestly reported).
- Untested dtype branches: BF16 kthvalue, int32/int64 radix encodings are template-generic with the executed FP32/FP16 instantiations and unchanged in value (`numeric_limits::max()` → same-valued compiler macros), but were not separately runtime-tested.
- Validation hardware is gfx1151/gfx1100; the reporter's gfx1200 was not directly tested (the fix has no arch-conditional code).
- The reporter-grade end-to-end scenario (`amp` behavior of a full training run on wheels) is outside this fix's claim; on this contributor's machine the observed AMP precheck behavior varied between otherwise-identical runs (one frozen run fell back to FP32, the latest-develop revalidation run kept genuine AMP) — raw logs for both are preserved and neither is claimed as the fix's effect.
- The new test's substitution guard rejects truncated kernels; a synthetic in-tree stub faking both identity markers is outside its threat model (hardening possible later).
- The manual-only `--mode=with-stl` variant reports FAIL (not INCONCLUSIVE) on hosts that have no standard library at all; it is never registered with CTest.

## Evidence

- Windows R2 freeze (full gate chain, adversarial matrices, DLL provenance, numerics, YOLO): [`AIwork4me/Ultralytics-Windows-ROCm-Training-RCA` branch `phase5.1/windows-r2-ci-portability-freeze` @ `c841716`](https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/tree/c841716) — manifest `findings/phase5_1_r2/FINAL_HANDOFF.json`, series SHA256 `48308f6d…`.
- Linux W7900 Phase 5.3 final A/B: [merged via PR #8](https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/pull/8) — verdict `PHASE5_3_LINUX_R2_AB_PASS_WITH_CTEST_SKIP` (kthvalue A/B, BatchNorm A/B, provenance, false-pass matrix 14/14).
- Latest-develop replay + revalidation (this phase): branch `phase5.4/windows-upstream-merge-readiness` (see `phase5_4/` evidence manifest).
- Patch integrity: R2 canonical per-patch SHA256 `816946b4…` / `46044d8c…` / `df7c3c3a…`, ordered series `48308f6d…` (`sha256_file_concat_v1`); this submission branch's re-exported patch files hash `da5a9de4…` / `6358142b…` / `69cbbb86…`, series `8e00f591…` — the **diff payloads are byte-identical**; only each file's `From <commit-sha>` header line differs (new commit identity after the replay).

## Related Issue

Fixes `ROCm/MIOpen#3956`

*(Note for reviewers: two commit messages contain bare references — `#3956` refers to the MIOpen issue above and `#3803` to MIOpen PR #3803 "All 7.0 hipRTC fixes"; the rocm-libraries repository has unrelated items with both numbers. `#3147` refers to rocm-libraries PR #3147, which is correct as written.)*
