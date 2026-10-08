# Upstream Base Assessment (Gate P5-02)

Date: 2026-10-08 (UTC). Frozen at the beginning of the Phase-5 run.

## Frozen upstream snapshot

```text
ROCm/rocm-libraries develop
7c5866144ac4b879be442563e2b49fa1c142ea36
"csrmv LRB: fix unsigned 32-bit overflow in grid_size (AISPARSE-662) (#11215)"
```

Phase 4 had observed develop at `18e1985`. Develop advanced by **7 commits**
(`18e1985..7c58661`); none of them touch `projects/miopen/` at all.

## Checks performed

### 1. Duplicate / equivalent fix detection — NEGATIVE (no equivalent fix)

- `git grep -l __has_include origin/develop -- projects/miopen/src/kernels/`
  → empty (no kernel adopts the self-containment pattern).
- `git ls-tree origin/develop -- projects/miopen/src/kernels/` contains no
  `miopen_freestanding_*` files.
- No MIOpen commit in `b68f894..origin/develop` mentions RTC, HIPRTC,
  type_traits, freestanding, or STL isolation.

Verdict: the fix has **not** landed upstream. Not
`BLOCKED — UPSTREAM ALREADY FIXED OR DUPLICATE`.

### 2. Affected-file drift — ZERO in all 8 files

All eight files touched by the validated series are byte-identical
(same Git blob OIDs) between the historical base `b68f894` and the frozen
develop `7c58661`:

| File | Drift |
|---|---|
| `projects/miopen/src/kernels/miopen_type_traits.hpp` | none |
| `projects/miopen/src/kernels/miopen_utility.hpp` | none |
| `projects/miopen/src/kernels/radix.hpp` | none |
| `projects/miopen/src/kernels/tensor_view.hpp` | none |
| `projects/miopen/src/CMakeLists.txt` | none |
| `miopen_freestanding_type_traits.hpp` / `_utility.hpp` / `_initializer_list.hpp` | absent upstream (ours to add) |

### 3. Ordered series applicability — CLEAN (sequential)

Method (avoids the Windows CRLF smudge trap: patches extracted as exact
Git blob bytes, not working-tree copies):

```text
worktree @ 7c58661
git apply 0001 → PASS
git apply --check 0002 (after 0001) → PASS
git apply 0002 → PASS
result: 8/8 files byte-equal (LF-normalized) to Phase-4 canonical content
```

Note: `git apply --check p1 p2` in a *single* invocation fails on 0002
because `--check` with multiple files validates each patch against the
original base, not cumulatively. Sequential application is the correct
method and passes.

### 4. MIOpen-wide drift b68f894 → 7c58661 — 9 files, none conflicting

`b68f894..origin/develop -- projects/miopen/` touches:

```text
M src/include/miopen/kern_db.hpp
M src/include/miopen/sqlite_db.hpp
M src/kernels/MIOpenBatchNormActivBwdSpatial.cpp
M src/kernels/MIOpenBatchNormBwdSpatial.cpp
M src/kernels/MIOpenBatchNormFwdTrainSpatial.cpp
M src/kernels/configuration.hpp
M src/kernels/default_configurations.hpp
M src/kernels/reduction_functions.hpp
M test/gtest/cache.cpp
```

Substance: a `use_amdgcn` → `use_gfx9_dpp` rename in the BatchNorm
configuration plumbing (+ small `default_configurations.hpp` /
`reduction_functions.hpp` tweaks, +18/−18 lines across the five kernel
files). The **include closure of `MIOpenBatchNormFwdTrainSpatial.cpp` is
unchanged** (same 8 `#include` lines) — the CI regression test's compile
surface is unaffected. No CMake test-infrastructure changes affect the
files our series touches.

### 5. HIPRTC compilation interface / kernel include closure

- No changes to `src/kernels` header-include structure between the two
  bases beyond the items above.
- The wheel HIPRTC used for validation (`amdhiprtc714060850.dll`,
  HIP 7.14.60850) is the same binary validated in Phases 3–4.

## Consequences for the Phase-5 candidate

- The Phase-5 candidate is **rebased onto the frozen current develop
  `7c58661`** (not the historical `b68f894`), per mission Gate P5-03.
- Because all 8 affected files are identical across the two bases, the
  source-fix content is **unchanged** from the validated P3/P4 bytes at
  this point; only the parent base moves (classified
  `UPSTREAM_BASE_CHANGE` in the P3→P5 delta).
- The later Windows DLL build compiles the develop BatchNorm kernel
  sources (`use_gfx9_dpp` rename) rather than the `b68f894` ones; this is
  upstream's own change, expected runtime-neutral, and disclosed in
  `docs/phase5/P3_TO_P5_DELTA.md`.

Verdict: **CLEAN — proceed with frozen develop `7c58661`.**

Not `BLOCKED_ON_UPSTREAM_BASE_DRIFT`; not a duplicate.
