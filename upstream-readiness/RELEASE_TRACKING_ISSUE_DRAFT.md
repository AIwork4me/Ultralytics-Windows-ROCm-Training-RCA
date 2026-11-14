# Issue draft — Windows ROCm PyTorch wheels do not yet include the MIOpen initializer-list fix (PR #13437)

**Target**: ROCm/rocm-libraries (release/packaging tracking) · **Status: READY — evidence complete, filed as release tracking (no code change required at ROCm side beyond cutting the next wheel)**

## Summary

PR #13437 (merged 2026-10-19, squash `f0a5d266`) fixes Windows spatial-BatchNorm training under HIP by supplying the missing MSVC STL runtime-compiler headers (`<initializer_list>` et al.) so hiprtc-generated kernel-skeleton code compiles without the host's MSVC STL being visible. The source chain carries the fix:

- rocm-libraries main ⊇ `f0a5d266` (verified via GitHub compare API)
- TheRock submodule bump `d875648` ⊇ `f0a5d266` (ahead_by=2/behind_by=0), TheRock main `9ea8cfc5` ⊇ fix (ahead_by=1011/behind_by=0)

**But no obtainable official Windows package contains it** (verified 2026-11-14, rescan `release-provenance/raw/official_wheel_rescan_20261114.json`):

| Channel | Newest Windows artifact | Contains fix? |
|---|---|---|
| repo.amd.com/rocm/whl-multi-arch (cp313 win_amd64) | torch 2.12.0+rocm7.14.1 | **NO** — MIOpen.dll `e97891df…`, fix-marker `miopen_initializer_list` count = 0 + behavioral EXPECTED_FAIL (exact #3956 signature with hidden host STL) |
| PyTorch official download.pytorch.org | no ROCm Windows wheels at all | N/A |
| TheRock releases | therock-10.1 (2026-10-05) predates the merge | NO |
| TheRock gfx1151 nightlies | stopped 2026-06-12 | N/A |

## User impact (concrete)

A Windows developer on the **official** wheel whose environment does not expose MSVC's STL headers (the normal case: plain conda/venv without a VS Build Tools installation) cannot train YOLO models with spatial BatchNorm on the GPU — kernel compilation fails during the first training step. Today the only workarounds are (a) installing MSVC Build Tools (undocumented requirement, version-sensitive) or (b) manually replacing MIOpen.dll with a source-built copy (unsupported). Both violate the expected "install official wheel → train" experience.

## What is needed

1. A Windows ROCm wheel release built from a commit ⊇ `f0a5d266` (the next 7.14.x/7.15 cut that includes TheRock submodule `d875648` or later).
2. Once published, we will re-run the full validation suite (G0 provenance → G1 primitives incl. the no-STL negative control → G2 7-task lifecycle → G3 AMP) against it and report results.

## Verification artifacts (all in-repo, SHA256-pinned)

- Fix-marker + behavioral proof: `release-provenance/raw/miopen_dll_inventory_raw.json`, `windows-training-validation/raw/envA_nostl_neg.log` (+ `.result.json` — the exact four-phase `#3956` signature on the official wheel)
- Lineage: `release-provenance/RELEASE_LINEAGE.md` (compare-API anchored, not date-inferred)
- Wheel manifest + binary provenance: `release-provenance/WHEEL_MANIFEST.json`, `BINARY_PROVENANCE.json`
- Weekly rescan: `release-provenance/raw/official_wheel_rescan_20261114.json`

*Hardware used for all behavioral proof: gfx1151 (Radeon 8060S), Windows 11 build 26200, torch 2.12.0+rocm7.14.1 official wheel.*
