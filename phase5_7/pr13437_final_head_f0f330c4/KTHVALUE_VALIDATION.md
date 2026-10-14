# Kthvalue / Radix Validation — final HEAD `f0f330c4` (leg E)

## Why this leg exists
The PR modifies `projects/miopen/src/kernels/radix.hpp` (unconditional
IWYU-style includes of `miopen_cstdint.hpp` + `miopen_type_traits.hpp`,
HIP headers only in the offline branch). kthvalue is the consumer that
runtime-compiles the radix kernels, so it needs explicit validation.

## Execution
- Binary: `C:\bfin\bin\test_kthvalue.exe`
  (SHA256 `aecb6ce4…`, built from clean `f0f330c4`)
- Run three times, all exit 0 / 27-27 PASS:
  1. default verbosity → `raw/kthvalue/E_kthvalue_patched.log`
  2. `MIOPEN_LOG_LEVEL=6` (same day, later) — served from the per-label
     kernel cache created by run 1; retained as
     `raw/kthvalue/E_kthvalue_patched_l6_runcachehit.log`
  3. `MIOPEN_LOG_LEVEL=6` with `USERPROFILE` redirected to an **empty**
     temporary home → `raw/kthvalue/E_kthvalue_patched_l6_isolated.log`
     — the primary evidence copy: MIOpen opens a fresh user kernel DB
     (`…\miopen_iso_home\.miopen\cache\3.6.2.f0f330c4\gfx1151_20.ukdb`),
     so the per-dtype compiles cannot be cache-served.

## Result (all three runs identical)
`[  PASSED  ] 27 tests.` — 3 suites × 9 cases:

| Suite | dtype | cases |
|---|---|---|
| `Smoke/GPU_Kthvalue_fwd_FP32` | FP32 | 9 |
| `Smoke/GPU_Kthvalue_fwd_FP16` | FP16 | 9 |
| `Smoke/GPU_Kthvalue_fwd_BFP16` | BF16 | 9 |

The gtest driver checks kthvalue outputs (values, and indices under the
documented tie semantics) against its reference within each case; PRNG seed
12345678 as printed by the driver. The previously published "27/27" figure
in the PR description is therefore **confirmed against the final HEAD**
(verified from these fresh logs, not copied).

GPU execution is real: the isolated level-6 log shows the runtime
compilation of `MIOpenKthvalue.cpp` through HIPRTC — **three fresh
compiles, one per dtype** (FP32 / FP16 / BFP16; each shows
`Unable to load binary` → `SaveBinary` against the empty kernel DB,
i.e. cache misses honestly compiled) — plus **27
`kernel_name = KthvalueFwd` launches** on `gfx1151` (one per test case).
`MIOpenKthvalue.cpp` includes the modified `radix.hpp`, so these compiles
exercise the changed include structure; the string "radix" itself does not
appear in kernel names. Within a single run, same-dtype cases after the
first reuse the in-process options-keyed cache entry — legitimate MIOpen
behavior; the empty-DB rerun exists precisely to make the compiles visible.

*Audit note:* an earlier level-6 rerun (retained as
`E_kthvalue_patched_l6_runcachehit.log`) was served entirely from the
per-label cache created by the first run — three `Successfully loaded
binary` hits, no compiles. The Gate B audit correctly rejected that log as
compile evidence; the isolated rerun above supersedes it.
