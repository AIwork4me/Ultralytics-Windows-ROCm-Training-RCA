# Phase-2 Summary (Gate 46)

Date: 2026-10-07. Branch `rca/windows-gfx1151-rocm714-phase2`.
Full trail: `docs/PHASE2_*.md`, `findings/phase2/`, `evidence/phase2/`
(315 checksummed artifacts), `scripts/phase2/` (repro bundle).

## Verdict

**LEVEL 3 PROVEN — a two-layer defect with exact upstream anchors.**

Ultralytics YOLO GPU training on native Windows (Radeon 8060S / gfx1151,
ROCm 7.14.0 pip wheels) failed because:

1. **Trigger (MIOpen source)** — commit `ce14dab3b92a82a…` (PR
   ROCm/MIOpen#3803, 2025-06-16, `miopen_type_traits.hpp`) and commit
   `b514736610` (PR #3147, 2025-12-18, `miopen_utility.hpp`, independently)
   gate those headers with
   `HIP_PACKAGE_VERSION_FLAT < 7000000000ULL`, so for HIP ≥ 7.0 the
   no-STL compatibility shim is disabled and runtime-compiled kernels
   unconditionally `#include <type_traits>` — an assumption that holds on
   Linux (system STL always present) but not on Windows wheels without
   MSVC.
2. **Exposure (wheel packaging/docs)** — AMD's Windows wheels ship an
   `x86_64-pc-windows-msvc`-target clang + hiprtc with **no C++ standard
   library, no include-path configuration, and no documented MSVC runtime
   prerequisite**. With no MSVC installed, every standard header resolves
   to nothing → `HIPRTC_ERROR_COMPILATION (6)` → `miopenStatusUnknownError`
   at the first spatial BatchNorm.

## Decisive experiment chain (all local, one-variable-per-step)

| # | Experiment | Result |
|---|---|---|
| 1 | Clean isolated env (Gate 22–23): curated 45-package clone, native stack SHA256-identical, paddlex-era packages absent | failure reproduces field-for-field → dirty-env hypothesis falsified |
| 2 | Standalone HIPRTC reproducer via ctypes (Gate 24): no torch/MIOpen/Ultralytics | control (no includes) compiles+executes; all 5 std headers fail → defect is in the toolchain layer, pre-MIOpen |
| 3 | Include discovery (Gate 25) | clang search list = resource dir + nonexistent VS8/9/10 fallbacks; every toolchain env var unset |
| 4 | MSVC discovery (Gate 26) | MSVC_ABSENT machine-wide |
| 5 | Install minimal VS Build Tools (Gate 27) → plain shell | standalone HIPRTC 6/6 PASS; minimal BN PASS; dev-shell arm PASS; INCLUDE-only arm PASS — plain-shell auto-discovery is the operative channel |
| 6 | Poisoned-header test (Gate 32) | wheel MIOpen honors `-I$ROCM_PATH/include`; the `-I` dir shadows MSVC discovery → clean injection channel proven |
| 7 | 48-line freestanding `type_traits` via that channel, cache-isolated, no MSVC dependency | ALL BN cases (3 shapes, eval, V1–V5) PASS + controls PASS |
| 8 | Naive DLL gate flip (`<7e9`→`<8e9`, length-preserving, backed up + restored + SHA256-verified) | still fails at the version-rotted shim (`false_type`/`enable_if`) → gate-number bump alone is NOT a fix; the shim needs repair |
| 9 | Regression matrix + numerics (Gates 33–34) | 8/8 PASS; GPU≈CPU to ≤7.2e-7 max abs; stats/gradients correct |
| 10 | YOLO closure (Gate 35) | amp=False AND default AMP: epoch+validation+weights+exit 0 on GPU, no MIOpen failures |
| 11 | Fresh-process, scrubbed env (Gate 36) | BN + YOLO PASS → no transient state required |
| 12 | Reboot persistence (Gate 37) | **NOT TESTED** (reboot impossible in-session; no persistence claimed) |

## User-level remedies validated (ranked)

1. **Install VS 2022 Build Tools with the C++ workload** (what this
   machine now has): zero-code, zero-config, auto-discovered. This is the
   practical fix for any affected user — but it is an *undeclared
   prerequisite* today (AMD docs don't mention it).
2. **`ROCM_PATH` + freestanding shim dir** (`patches/shim_stl/`): no
   admin, no DLL changes; validated end-to-end FOR THE BATCHNORM CLOSURE
   (a type_traits-only shim covers BN; non-BN composable-kernel RTC
   kernels that consume `<utility>` would need the shim extended) and
   proven NOT to rely on MSVC (the `-I` dir shadows MSVC discovery —
   poisoned-header proof). User-level workaround, not an upstream fix.

## Upstream-quality fixes identified (recommendation only; nothing submitted)

- **rocm-libraries/MIOpen**: repair the RTC self-containment — make the
  no-STL traits shim unconditional for `MIOPEN_HIP_RUNTIME_COMPILE` on all
  HIP versions, fixing the rotted window-gated block (real `enable_if`,
  not `__hip_internal`) — shape in
  `patches/candidate_B_miopen_type_traits.patch`. Needs Linux HIP≥7
  regression runs + coverage for other std-using RTC kernels
  (`<utility>` consumers).
- **TheRock / wheel pipelines**: bundle a freestanding std-subset (or full
  STL) for the wheel clang and point hiprtc/MIOpen at it (the
  `-I$ROCM_PATH/include` channel already exists and is honored).
- **ROCm docs**: declare the MSVC C++ Build Tools runtime prerequisite for
  Windows pip-wheel users until either of the above lands.

Phase-2 stopped **before** any upstream PR/issue/comment, as mandated.
`pr_created: false`.
