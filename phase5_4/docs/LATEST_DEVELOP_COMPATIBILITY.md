# LATEST DEVELOP COMPATIBILITY AUDIT — Gate P54-01

Mission: `WINDOWS-P54-MIOPEN-UPSTREAM-MERGE-READINESS`
Audit performed: 2026-10-09 (UTC) · Auditor: Windows Phase 5.4 agent

## 1. Latest upstream observation

| Field | Value |
|---|---|
| Repository | `ROCm/rocm-libraries` (fetch via local partial clone, ref `origin/develop`) |
| Develop SHA | `681bc9edc37e8ceceb1c8227d8e63fc2ea9f5243` |
| Commit date | `2026-10-09T10:39:02Z` — `fix(miopen): reject reduce tensors that do not fit the int32 legacy kernels (#12874)` |
| Identical to mission-briefing SHA? | **YES** (`681bc9ed…` observed at mission start and re-queried during this gate) |
| Distance from R2 base `7c586614` | 61 commits ahead, 0 behind |
| Merge-base | `7c5866144ac4b879be442563e2b49fa1c142ea36` (= R2 base; pure fast-forward, no divergence) |

## 2. Changed commits touching `projects/miopen` (5 of 61)

| Commit | Subject | Files |
|---|---|---|
| `681bc9ed` | fix(miopen): reject reduce tensors that do not fit the int32 legacy kernels (#12874) | `src/reducetensor.cpp` (+183/−95), `src/reducetensor_api.cpp`, `test/gtest/reduce_shape_limits.cpp` (new), `CHANGELOG.md` |
| `be3dcc97` | fix(miopen): Remove direct __ocml calls (#13312) | `src/kernels/miopen_math.hpp` (41 lines) |
| `cf0ac8d1` | fix(miopen): hold ConvHipConv out of the perf-config picker (#13337) | `src/conv/heuristics/lgbm_pcfg_pick.cpp` |
| `7f6056ac` | fix(miopen): correct gfx1250 depthwise test applicability (ALMIOPEN-2841) (#13289) | `test/gtest/unit_conv_solver_ConvCkGroupedConvFwd.cpp` |
| `4e3c99c4` | fix(miopen): Remove broken single-argument __half fmin/fmax/pow (#13190) | `src/kernels/miopen_math.hpp` |

## 3. R2 changed-file set audit (blob identity, `git rev-parse <rev>:<path>`)

Six files pre-existing upstream — **blob-identical between R2 base and latest develop**:

| File | Blob @ base | Blob @ develop | Same |
|---|---|---|---|
| `src/CMakeLists.txt` | `19dce8c1…` | `19dce8c1…` | ✅ |
| `src/kernels/miopen_type_traits.hpp` | `e2b6a98e…` | `e2b6a98e…` | ✅ |
| `src/kernels/miopen_utility.hpp` | `156cb30f…` | `156cb30f…` | ✅ |
| `src/kernels/radix.hpp` | `f8a91fed…` | `f8a91fed…` | ✅ |
| `src/kernels/tensor_view.hpp` | `36ddef6d…` | `36ddef6d…` | ✅ |
| `test/CMakeLists.txt` | `f6a0e662…` | `f6a0e662…` | ✅ |

Four files introduced by R2 — **absent at base AND at develop** (no name collision, no equivalent upstream functionality added in the window):

| File | Present @ develop |
|---|---|
| `src/kernels/miopen_freestanding_type_traits.hpp` | ❌ absent |
| `src/kernels/miopen_freestanding_utility.hpp` | ❌ absent |
| `src/kernels/miopen_freestanding_initializer_list.hpp` | ❌ absent |
| `test/hiprtc_selfcontained.cpp` | ❌ absent |

Complete `projects/miopen/src/kernels/` diff base→develop is exactly one file: `miopen_math.hpp`.

## 4. Indirect dependency audit

- **RTC include closure of the R2 regression test**: the test compiles `MIOpenBatchNormFwdTrainSpatial.cpp`, which includes `miopen_math.hpp` (at base and at develop — include line unchanged). `miopen_math.hpp` IS upstream-changed in this window. Assessment: the change replaces `__ocml_*` device-library calls with compiler builtins (`__builtin_amdgcn_exp2f`, `__builtin_amdgcn_logf`, `__builtin_fminf16`, `__builtin_fmaxf16`) and `__half` intrinsics (`hsqrt`, `hrsqrt`, `__habs`), and removes single-argument `__half fmin/fmax/pow`. All replacements are compiler-provided (no host C++ standard library dependency) — the change moves in the *freestanding-safe direction* and removes an OCML dependency rather than adding one. No `<…>` host-stdlib include is introduced. Expected compatible; **empirically re-proven by fresh Windows rebuild + full test matrix in Gate P54-04** (this audit deliberately does not treat file-level reasoning as build proof).
- **HIPRTC CMake targets/exports**: no MIOpen CMake file changed in the window (`projects/miopen/**` CMake diffs: none). The `hiprtc::hiprtc` / plain-`hiprtc` linkage strategy from R2 patch 3 therefore targets unchanged logic.
- **Test-registration helpers / test-selection policy**: `test/CMakeLists.txt` unchanged → R2's registration block applies against identical context; skip-list/`MIOPEN_TEST_GDB` machinery untouched.
- **Kernel include search paths / runtime compile definitions**: `src/CMakeLists.txt` unchanged → include-dir export list and `MIOPEN_*` compile definitions consumed by the test unchanged.
- **CMake toolchain requirements**: all CMake changes in the window are in other projects (`rocke`, `composablekernel`, `hipblaslt`, `hipfft`, integration-tests); none in `projects/miopen` or repo-level `cmake/` consumed by the MIOpen build.
- **API changes influencing the test**: `reducetensor.cpp` (public-API fix) and solver heuristics are outside the R2 test's compile/dispatch surface (test targets BN spatial kernel only).
- **`miopen_cstdint.hpp`** (upstream's own freestanding-style kernel header for integer typedefs, merged via #12623 on 2026-09-29, before R2 base): present and **unchanged** base→develop. Upstream precedent for the R2 freestanding-header pattern is therefore stable across this window.

## 5. Overlapping-work search (GitHub, 2026-10-09)

- **Open PR #12733** `fix(miopen): resolve HIPRTC bf16 regression (ALMIOPEN-2519)` (opened 2026-09-29): touches `src/comgr.cpp`, `src/kernels/MIOpenCheckNumerics.cpp`, `src/kernels/miopen_conv3d_depthwise_fwd.cpp`, `src/kernels/miopen_limits.hpp`, `src/solver/conv/conv_3d_depthwise_fwd.cpp`. **File set disjoint from all ten R2 files.** Same problem *class* (HIPRTC lacks host dev headers on runtime-only installs) but different root cause (BF16 preamble type availability `__hip_bfloat16` vs `hip_bfloat16`, not host-STL `<type_traits>` reachability). Non-competing; corroborates the PR motivation.
- No open or merged PR matches `freestanding` or `hiprtc_selfcontained` (0 hits each).
- Merged precedents (both predating R2 base, already contained in it): #10995 `guard HIPRTC includes in ConvDepthwiseFwd3D kernel` (2026-08-26); #12623 `miopen_cstdint.hpp` LP64 fix (2026-09-29).
- **Issue `ROCm/MIOpen#3956`** ("Running BatchNorm2D causes miopenStatusUnknownError"): still **OPEN**, 0 comments, label `status: triage`, created 2026-04-22. No upstream fix merged for it in this window. (Full mapping in Gate P54-07.)

## 6. Classification

Per the mission taxonomy:

- **A. No relevant upstream changes** — applies to all ten R2 files (blob-identical or absent) and to MIOpen CMake/test-registration logic.
- **C. Relevant but compatible changes** — `miopen_math.hpp` sits inside the R2 test's RTC compile closure and changed; analysis says compatible (builtin-ward direction), Gate P54-04 provides the empirical proof.
- **B. Non-overlapping changes** — PR #12733 (open) and the reduce/gfx1250/heuristics commits.
- **D. Conflicting or superseding changes** — **none found.**

## 6a. Post-review addendum (independent reviewer findings, incorporated)

The Gate P54-01 independent reviewer (PASS/GO) identified two open upstream PRs outside the 61-commit window that are latent merge-order risks for the eventual submission (no impact on the frozen replay):

- **Open PR #10945** `feat(miopen): add ConvDepthwiseDirect solver for RDNA depthwise convolution` — touches `projects/miopen/src/CMakeLists.txt`, one of the ten R2 files.
- **Open PR #10426** `fix(miopen): make the _accumulate type-mismatch static_assert actually fire` — touches `projects/miopen/src/kernels/batchnorm_functions.hpp`, inside the R2 test's RTC include closure.

Reviewer's strengthened analysis of `miopen_math.hpp`: at base, the removed one-arg `__half fmin/fmax/pow` overloads were infinitely recursive (called nonexistent one-arg `_Float16` versions); every `fmin/fmax/pow` call site in the test kernel's include closure is two-arg and `miopen::`-qualified — no closure risk. The entire `MIOpenBatchNormFwdTrainSpatial.cpp` file is blob-identical base→develop, not merely its include line. Residual static-analysis limit: availability of `__builtin_fminf16`/`__builtin_amdgcn_logf` under the Windows hipRTC clang — deferred to Gate P54-04 empirical proof.

## 7. Conclusion

Latest develop (`681bc9ed`, unchanged since mission briefing) is **61 commits ahead of the R2 frozen base with zero changes to any of the six upstream files R2 modifies, zero name collisions for the four new files, and no overlapping or superseding upstream work**. The single in-closure change (`miopen_math.hpp`) trends freestanding-safe. A clean `git am` replay is expected and is tested next in Gate P54-02; build/runtime compatibility is *not* claimed from this audit alone and will be established empirically in Gate P54-04.

**Verdict: COMPATIBILITY EXPECTED — CLEAN REPLAY ANTICIPATED (classification A+C, no D).**

## 8. Develop-drift addendum (final check, 2026-10-09 later same day — Reviewer D finding)

Upstream `develop` advanced **after** the candidate froze on `681bc9ed`: observed mid-panel at `5af159d6`, and at the final check at **`aa966601086ab87fdc1ccedbbdb6865f9526d382`** (3 commits past the candidate base: `45b3ec92` fix(rocke), `5af159d6` test(hipdnn), `aa966601` feat(tensilelite) — all in **other projects; zero `projects/miopen` files touched**). The ten-file blob audit was re-run against `aa966601`: **all ten blob-identical** (six upstream files unchanged, four R2 files still absent).

Per the mission rule, the candidate's tested base is **NOT silently changed** — it remains pinned at `681bc9ed`. A submission-day develop refresh (SUBMISSION_DAY_CHECKLIST §1) is mandatory: the recorded expectation is a clean replay onto any fast-forward tip while the ten-file audit stays identical, but that expectation must be re-verified (minimum: blob audit + regression-test build + ctest) on the submission-day tip before pushing a branch.
