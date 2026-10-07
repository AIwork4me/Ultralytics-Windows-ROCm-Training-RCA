# Phase-2 Cross-Version Reasoning (Gate 38)

Local vs external evidence kept strictly separate. The main environment
was NOT upgraded (ROCm 7.14.0 wheels unchanged throughout; SHA256-verified
before/after every machine-state change).

## Local evidence (this machine, this RCA)

| Item | Value | Where established |
|---|---|---|
| ROCm 7.14.0 wheels (rockrel build) | defect present; BN RTC fails at `<type_traits>` | Phase 1 + Gate 23 |
| HIP runtime 7.14.60850, MIOpen 3.5.2 | gate `HIP_PACKAGE_VERSION_FLAT < 7000000000ULL` present in embedded header → HIP ≥ 7.0 → real-STL path | Gate 29 (extracted tree + upstream) |
| gfx1151 (Radeon 8060S) | compile target; failure is header-resolution, not arch-specific (code would compile past includes for any arch) | Gates 24/32 |
| Python 3.13.16 (clean env) vs 3.13.13 (base) | failure identical in both → Python-version-independent (consistent with the defect living in native compile) | Gates 21–23 |

## External evidence (not locally re-tested)

| Item | Source | Relation to local mechanism |
|---|---|---|
| ROCm 7.2.1, gfx1200, Python 3.12.7 — identical compiler-diagnostic signature | MIOpen #3956 (open; Phase-1 C022) | Same HIP 7.x family → same `HIP_PACKAGE_VERSION_FLAT ≥ 7.0` gate → same real-`<type_traits>` requirement on a wheel without STL. Mechanism now *locally proven* for 7.14; for 7.2.1 it remains signature-level correlation (claimed carefully, not proven). |
| gfx1200 (discrete RDNA4) affected | #3956 | Falsifies gfx1151-specific theories (as in Phase 1) — consistent with a host-toolchain defect, not a GPU-arch defect. |
| TheRock Windows builds: MSVC 19.43+ documented as build prerequisite | TheRock `docs/development/windows_support.md` (Gate 29 fetch) | Explains why TheRock-built Windows stacks could resolve std headers (build env had MSVC; #2169's log compiled past the include chain). Does NOT prove the #2169 user machine had MSVC — plausibility only. |
| rocm-libraries #2169 (gfx1151, Oct 2025) | Phase-1 C025 | Different compile-stage defect (DPP inline asm, fixed by PR #1288); its log passing the include chain is the packaging-difference lead, now explained by the TheRock/MSVC observation above (plausible, not proven). |
| rocm-libraries #2169-era BN via OpenCL `.cl` path (MIOpen 3.5.1 cache on this machine, Jul 2025) | Phase-1 P10d | BN's move from OpenCL path to HIPRTC `.cpp` path exposed the previously-hidden std-header dependency. |

## Version-gate arithmetic

`HIP_PACKAGE_VERSION_FLAT` = `M*1e9 + m*1e6 + p*1e3`-style 10-digit
encoding (e.g. 6.0.25 → `6000025000`): every HIP 7.x (7.0 … 7.14) exceeds
`7000000000ULL`, so **all HIP ≥ 7.0 MIOpen rockrel-era Windows wheels carry
the real-STL requirement in RTC mode**; conversely HIP 6.x wheels used the
shim (with the 6.0.25–6.1.24 window caveat found in Gate 32). This predicts
the defect window starts at the first ROCm-7 Windows wheel that ships
MIOpen with PR #3803 (merged 2025-06-16) — consistent with #3956 appearing
on 7.2.1 (first public 7.x line many Windows users had) — and persists
through 7.14 (locally proven). ROCm 10.x stable-index wheels (2.12.0+rocm10)
were not tested and are NOT claimed.

## What Phase 2 does NOT claim

- No claim that ROCm 10.x wheels are fixed or broken (untested).
- No claim that #3956's machine lacked MSVC (unverifiable from the issue).
- No claim the TheRock wheel of Oct 2025 bundled an STL (only that its
  build environment required MSVC; runtime behavior on the reporter's
  machine is unproven).
