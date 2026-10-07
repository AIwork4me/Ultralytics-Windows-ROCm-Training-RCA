# Phase-3 Summary — Upstream Patch Closure

Date: 2026-10-07. Branch `rca/windows-gfx1151-rocm714-phase3`.
Full trail: `docs/phase3/*`, `findings/phase3/*`, `evidence/phase3/`
(checksummed), `scripts/phase3/` (reusable harness), `patches/phase3/`
(final artifacts + history).

## What Phase 3 set out to do and did

Turn the Phase-2 LEVEL-3 RCA into a validated upstream patch: patch REAL
rocm-libraries source, build REAL patched MIOpen on Windows, make
PyTorch load it, prove the original BatchNorm failure disappears via the
source fix alone (no MSVC), validate numerics and YOLO end-to-end, audit
the full RTC std-header scope, check cross-version/cross-platform
behavior, and package everything for maintainer review — WITHOUT
submitting anything upstream.

## Result

**WINDOWS PATCH CLOSURE — PASS. UPSTREAM PR READINESS — BLOCKED ON LINUX
REGRESSION** (no Linux ROCm GPU environment available; sanctioned
outcome per the brief).

## The final patch (what a maintainer receives)

Two commits against rocm-libraries develop (`b68f8944`), 560 diff lines:

1. `0001` — the defect fix (#3956 class): keep real `<type_traits>` /
   `<utility>` whenever `__has_include` proves them reachable (Linux and
   Windows+MSVC behavior byte-identical to develop), fall back to new
   self-tested freestanding headers only where NO standard library
   resolves — the state where compilation previously always failed.
   Partial/inconsistent STL states fail loudly (`#error`) instead of
   double-defining (prevents the #7718 failure class). HIP<7 legacy
   arms untouched. Headers registered in the embedded-kernel list.
2. `0002` — residual coverage from the 104-kernel audit: radix.hpp
   (compiler builtin limits + `miopen_cstdint` routing) and
   tensor_view.hpp (`initializer_list` availability probe + clang-lowered
   freestanding fallback).

Plus a proposed CI test (compile-only, no GPU, negative-control capable)
and a complete PR-draft/maintainer-report/routing-plan set.

## Evidence highlights (all archived + SHA-verified)

- **Single-variable no-MSVC A/B** (MSVC include tree renamed away): wheel
  MIOpen → exact original failure (`miopen_type_traits.hpp:151
  'type_traits' file not found`, exit 1); patched build → PASS (exit 0).
  Re-proven on the final build.
- **Real builds, really loaded**: three patched builds (V1/V2/V3) from
  develop with the wheel's own clang/LLVM+lld-link; per-run
  GetModuleFileNameW provenance shows the wheel-path DLL with the build's
  SHA256 in every validation record.
- **Full matrix green on the final build**: BatchNorm (minimal/#3956/
  YOLO-like/BN1d-3D/BN2d/BN3d, train+eval) ≤9.5e-7 vs CPU; 11-op non-BN
  RTC matrix in BOTH STL states; YOLO26n coco8 1-epoch training in both
  amp modes.
- **The embed-list catch**: binary-provenance checking (Gate 61) caught
  that new headers weren't in the embedded-kernel list — fixed before
  any runtime test could silently pass.
- **The reviewer-B catch**: an adversarial falsifier proved (by live
  compilation) that V2's radix change would have broken kthvalue RTC
  compilation on ALL platforms — including a Linux regression. Fixed
  with compiler builtin limits; kthvalue TU now compiles in both STL
  states.
- **Partial-STL hardening**: the probe-invariant attack (this repo's own
  Phase-2 shim creates that state!) now fails loudly — verified live.

## Honest limits

- Linux HIP≥7 regression runs: BLOCKED (environment). The design keeps
  STL-present behavior byte-identical, but Linux CI must confirm before
  merge — exact requirements documented for the submitter.
- ROCm 7.2.1 runtime: NOT TESTED (wheels delisted); source gate verified
  present in the `rocm-7.2.1` tag.
- Author identity/DCO sign-off: deliberately left as placeholders for
  the human submitter.
- CK disabled in the validation build (documented deviation; conv
  coverage unaffected in testing).

## Status of the four remedies (Gate 79)

1. MSVC Build Tools — existing-user remedy (unchanged, validated Phase 2).
2. ROCM_PATH shim dir — user workaround (now formally a PARTIAL-STL
   state that the patched MIOpen rejects loudly; users on patched builds
   should remove it).
3. **MIOpen source patch — this package (Windows-validated).**
4. Wheel STL bundling — routed to TheRock (+clr lane), re-prioritized
   first in the routing plan per review.

UPSTREAM PR CREATED: NO · ISSUE: NO · COMMENT: NO. Stopped for
human/ChatGPT review.
