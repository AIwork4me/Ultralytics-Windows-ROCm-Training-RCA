# P16 WINDOWS RELEASE OWNER MAP (2026-11-15)

Per mission §5.1: trace the exact release ownership of the merged MIOpen fix (rocm-libraries PR #13437, squash `f0a5d266`, merged 2026-10-19) into a published Windows artifact. P16 re-verified every stage live; stage facts unchanged since P15 unless noted.

| # | Stage | Owning repo / channel | Ref | Last verified state (2026-11-15) | Blocking dependency |
|---|-------|----------------------|-----|----------------------------------|---------------------|
| 1 | MIOpen source fix | ROCm/rocm-libraries (MIOpen subtree) | PR #13437 squash `f0a5d266` | merged 2026-10-19; on develop/main | — (done) |
| 2 | MIOpen submodule pin in TheRock | ROCm/TheRock (`thirdparty/miopen` or equivalent) | main submodule `9ea8cfc5` ⊇ `f0a5d266` (compare API behind_by=0, verified P15) | **unchanged**: main contains the fix | — (done) |
| 3 | Release cut (tag) | ROCm/TheRock releases | newest tag `therock-10.1` published **2026-10-05** | **unchanged** — re-checked today: no tag newer than 10.1 | **A post-2026-10-19 release cut does not exist yet** |
| 4 | Windows SDK wheel build | TheRock → `rocm_sdk_core/libraries/device-*` win_amd64 wheels on `stable.repo.amd.com/rocm/whl-next/` | `rocm_sdk_libraries-10.1.0` (Last-Modified 2026-10-05) | re-downloaded today, SHA byte-identical to P15 audit; embedded MIOpen.dll `3.6.1.39d8d603`, fix marker 0 (see P16_OFFICIAL_WHEEL_BINARY_AUDIT.md) | Needs a build from a post-fix MIOpen |
| 5 | Architecture kernel/device package | `amd_torch_device_gfx1151` / `rocm_sdk_device_gfx1151` wheels | newest 2.14.0+rocm10.1.0 / 10.1.0 | present and functional (P14: real GPU compute OK on gfx1151) | Depends on stage 4 |
| 6 | PyTorch Windows wheel | `torch-2.14.0+rocm10.1.0-cp313-win_amd64.whl` (whl-next); `torch-2.12.0+rocm7.14.1` (whl-multi-arch) | both channels re-scanned today — **no new version** | installs + real GPU compute (P14) | Depends on stage 4 |
| 7 | PyTorch official index | pytorch.org / pytorch/pytorch | **zero ROCm Windows wheels** (verified P15) | unchanged | Independent of stages 1–6 |
| 8 | Official installation documentation | rocm.docs / hyperscale docs | Windows PyTorch install docs point at whl channels | points at the PRE-FIX wheels | Follows stages 4–6 |

## Cut point (unchanged from P15, re-confirmed today)

The single missing step is **a post-2026-10-19 MIOpen → TheRock release cut → Windows SDK/wheel build → publish cycle**. The fix is on the source path (stages 1–2 ✓) but no release slice after 2026-10-19 exists (stage 3 ✗), so every published binary predates the fix (stages 4–6 ✗).

**Owner**: AMD/TheRock release chain (scheduling), tracked in [rocm-libraries#15862](https://github.com/ROCm/rocm-libraries/issues/15862) with the P14/P15 maintainer-ready handoff evidence (P15 comment 2026-11-15T02:09Z). No code defect has been identified in the packaging chain — the fix is simply not yet in any release cut — so per mission §5.4 no packaging PR is submitted; the handoff evidence is the correct deliverable.
