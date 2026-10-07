# Phase-3 Gate 75 — Cross-Platform Validation Summary

Date: 2026-10-07.

| Platform | HIP | GPU | Unpatched | Patched | Numerics |
|---|---:|---|---|---|---|
| Windows gfx1151 (this machine, ROCm 7.14 wheels) | 7.14.60850 | Radeon 8060S | **tested** — `miopen_type_traits.hpp:151 'type_traits' not found` → `HIPRTC_ERROR_COMPILATION(6)` → exit 1 (live A/B, MSVC include tree renamed away; `g63_A_wheel_nomsvc_v2.json`) | **tested** — V1 `0a0878db` and V2 `0d40bf5b` builds: BN all variants, 11-op non-BN matrix, YOLO26n coco8 both amp modes — all PASS, no host STL (same no-MSVC state) | **tested** — BN max_abs ≤ 9.5e-7 vs CPU, running stats ≤ 1.2e-7, grads finite (`g65_66`, `g78_v2_matrix`) |
| Windows second version (ROCm 7.2.1, #3956's stack) | 7.2.1 | gfx1200 (external report) | **externally correlated** — MIOpen#3956 reports the identical signature; source gate VERIFIED present in `rocm-7.2.1` tag (identical outer `HIP_PACKAGE_VERSION_FLAT < 7000000000ULL` gate; inner macro is the pre-rename `MIOPEN_DONT_USE_HIP_RUNTIME_HEADERS`) | **not tested** — artifact unavailable (7.2.1 wheels delisted from AMD indexes; only 7.13/7.14/10.1 listed; archived wheel URL 403). Patch semantics apply unchanged (same structure, renamed macro) | not tested |
| Linux (HIP ≥ 7, AMD GPU) | — | — | **reasoned only** — Linux has system STL reachable by hiprtc's default search; the HIP≥7 gate's assumption holds there (Phase-2 §4 platform asymmetry) | **NOT TESTED — BLOCKED: no Linux ROCm GPU environment available** (see Gate 71 record) | not tested |

Legend: tested = executed locally with archived evidence; externally
correlated = upstream report + source verification; reasoned only =
analysis without execution; not tested = no claim made.

## Linux blocking record (Gates 71-74)

No Linux AMD-GPU ROCm environment is accessible from this investigation
(native Windows workstation only; no cloud credentials provisioned for a
ROCm Linux instance in this engagement). Per the Phase-3 brief:
**"BLOCKED — no Linux ROCm GPU environment available"** → PR readiness is
capped at *Windows-validated, Linux-regression-pending*. The design
minimizes the Linux risk class analytically (PATCH_DESIGN.md): on any
environment where `<type_traits>`/`<utility>`/`<initializer_list>` are
reachable — true for stock Linux — the patched wrappers evaluate
byte-identically to today's develop behavior (`__has_include` true → real
STL); the freestanding arm only activates where compilation previously
always failed. The residual Linux-specific risk is a toolchain without
`__has_include` support (pre-clang-5 / unusual vendors) — not known to
exist in supported MIOpen CI toolchains, but flagged for the maintainer.

## Version-window statement

- First release carrying the #3803 gate (type_traits): HIP/ROCm 7.0.x
  line (commit `ce14dab3`, merged 2025-06-16).
- The utility gate (`b514736610`, 2025-12-18) landed in the 7.2.x line.
- Gate still present in develop = the ROCm 10.x source line (fetched
  2026-10-07, byte-identical wrappers).
