# RELEASE LINEAGE — PR #13437 to official packages

Rechecked live: **2026-11-14** (all GitHub facts via `gh` API on ROCm orgs).

## 1. Source chain (all steps PROVEN)

```
ROCm/MIOpen issue #3956 (Windows HIPRTC + host STL dependency)
  └─> ROCm/rocm-libraries PR #13437  "MIOpen: make HIPRTC kernel includes
        self-contained without host STL"
        MERGED 2026-10-19T09:27:09Z  →  squash-merge commit
        f0a5d2664cf3334161f7b82c02dfcd2213988a8a          [gh api: state=MERGED]
  └─> ROCm/TheRock PR #9359  "Bump rocm-libraries from cb26189 to d875648"
        MERGED 2026-10-20T23:15:52Z  →  merge commit
        b0958085a97cb03a2c38931b8e2ec86ac78d1563          [gh api: state=MERGED]
        bump target d8756483d66d58e7eac956decdc3abbfeb4b05fd
          contains f0a5d266:  compare API status=ahead, ahead_by=2, behind_by=0
  └─> TheRock `main` (default branch) 2026-11-14:
        rocm-libraries submodule pointer 9ea8cfc5e4310730186f80b18226b792418b2bd8
          contains f0a5d266:  compare API status=ahead, ahead_by=1011, behind_by=0
```

Verification method: GitHub compare endpoint
`repos/ROCm/rocm-libraries/compare/f0a5d266…<head>` returns `behind_by: 0` only when the
merge commit is an ancestor of the head — used instead of release-date inference
(mission G0.1 requirement). Cherry-pick/backport scan: none observed (straight bumps).

## 2. Release tags → do they contain the fix?

| TheRock tag | Date | vs merge date 2026-10-19 | Contains fix? |
|---|---|---|---|
| therock-10.1 | 2026-10-05 | before | **NO** (PROVEN by date; no post-merge source reached release branch) |
| therock-7.14.1 | 2026-08-31 | before | **NO** |
| therock-10.0 | 2026-08-26 | before | **NO** |
| therock-7.14 | 2026-07-15 | before | **NO** |
| (no tag after 2026-10-20 exists as of 2026-11-14) | — | — | — |

`gh release list --repo ROCm/TheRock` (2026-11-14): latest listed = `therock-10.1` (marked
Latest). **Zero release tags postdate the merge** → no official release can contain the fix.

## 3. Downstream distribution channels (2026-11-14)

| Channel | Newest state observed | Contains fix? |
|---|---|---|
| AMD official PyTorch index `repo.amd.com/rocm/whl-multi-arch/` (cp313 win_amd64) | torch 2.12.0+rocm7.14.1 (+ torchvision 0.27.0) | **NO** — behavioral proof: BN fails exact #3956 signature with hidden host STL (historical: `C:\YOLO_PR13437_PostMerge\logs\official\batchnorm_nostl_vctools.log`, in-repo copy `raw/batchnorm_nostl_vctools_C+D_mission.log`; re-confirmed 2026-11-14 on `windows-training-validation/raw/envA_nostl_neg.log`); fix-marker `miopen_initializer_list` = 0 in installed MIOpen.dll `e97891df…` (raw count records: `raw/miopen_dll_inventory_raw.json`) |
| PyTorch official `download.pytorch.org/whl/` Windows | **no ROCm wheels at all** (0 matches `rocm…win_amd64` in torch index) | N/A |
| TheRock nightly pip index `rocm.nightlies.amd.com/v2/gfx1151/` | **stale at 2026-06-12** (torch + rocm-sdk-libraries-gfx1151); no 7.14.1+/post-merge builds | **NO** |
| TheRock S3 dev artifacts (`therock-nightly-artifacts`, windows platform dir) | not a pip index; no installable official Windows wheel with fix located | UNKNOWN (no public wheel found) |

Conclusion: **no obtainable official release package contains PR #13437** as of 2026-11-14.
The next official release cut from TheRock main (or a 7.14.2/10.2 patch carrying the fix)
is the gating event for release closure — see G0_VERDICT.md.

## 4. What an official inclusion will look like (checklist for re-run)

1. New TheRock release tag ≥ 2026-10-20 merge, or 7.14.x/10.x patch release whose
   rocm-libraries submodule pointer passes `merge-base --is-ancestor` vs `f0a5d266`.
2. AMD torch wheel (or TheRock wheel) built from that tag lands on
   `repo.amd.com/rocm/whl-multi-arch/` (or nightlies resume for gfx1151).
3. Installed `_rocm_sdk_libraries/bin/MIOpen.dll` contains fix-marker
   `miopen_initializer_list` ≥ 1 and passes the no-STL BatchNorm gtest/Python probe.
4. Cross-check `download.pytorch.org/whl/torch/` for any ROCm **Windows** wheel (as of
   2026-11-14 there are none — a future appearance would be a new release channel to
   scan; audit fix A-F6). Also note the AMD multi-arch index now carries a
   torch-2.13.0+rocm7.14.0 **linux_x86_64** series (observed 2026-11-14, no Windows
   wheel) — track it in the weekly scan (audit obs A-F8).
