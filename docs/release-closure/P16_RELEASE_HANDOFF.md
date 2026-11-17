# P16 RELEASE HANDOFF (2026-11-15)

Mission §5.4 deliverable. Status: **no packaging code defect found → no code PR submitted**; the obstacle is release scheduling (the fix exists on the source path, no release cut after 2026-10-19 carries it). This file is the current handoff pointer; the living handoff is [HANDOFF.md §7](HANDOFF.md) and the full maintainer-ready evidence stands in the rocm-libraries#15862 tracker.

## Handoff summary for the release owner (AMD/TheRock)

| Item | Value |
|------|-------|
| Current published binary | `rocm_sdk_libraries-10.1.0-py3-none-win_amd64.whl`, SHA256 `0c34bafb…55e952f`, embedded MIOpen.dll SHA256 `266d716b…c1429b4`, version `3.6.1.39d8d603` |
| Missing source commit | MIOpen freestanding-header fix, rocm-libraries PR #13437 (squash `f0a5d266`, merged 2026-10-19) — already on develop/main and TheRock main submodule |
| Exact affected package | `rocm_sdk_libraries` (win_amd64) on `stable.repo.amd.com/rocm/whl-next/` → consumed by `torch-2.13.0/2.14.0+rocm10.1.0` Windows wheels; same defect in `torch-2.12.0+rocm7.14.1` on `repo.amd.com/rocm/whl-multi-arch/` (MIOpen 3.5.2.cd957402) |
| Reproducer | MIOpen issue #3956 minimal BatchNorm repro; no-STL method `VCToolsInstallDir → empty dir` (P13437-verified technique); raw FAIL logs archived in this repo |
| Required release cut point | TheRock tag > `therock-10.1` (2026-10-05), i.e. any tag cut after 2026-10-19, followed by the Windows SDK wheel build → publish to whl-next |
| Minimal acceptance script | (1) wheel SHA recorded; (2) extract `_rocm_sdk_libraries/bin/MIOpen.dll`; (3) assert version string build-commit ≥ `f0a5d266` and `miopen_initializer_list` marker ≥ 1 (post-fix reference = 2); (4) run the no-STL BatchNorm repro → expect PASS; (5) `yolo train` on gfx1151 with the official stack → expect PASS |
| User-facing impact | Every current official Windows ROCm PyTorch install fails real GPU BatchNorm training without an undocumented host MSVC STL repair; correct training only on the engineering-reference source build |
| Packaging owner action | Cut a post-fix release slice; nothing else in the chain blocks (per-arch device packages and torch wheels already functional, P14) |

## P16 deltas vs P15 handoff

1. Channels re-scanned 2026-11-15 — **no new artifact** (no rocm 10.2.0, no TheRock tag newer than `therock-10.1`).
2. Byte-identity of the audited wheel re-proven by re-download + SHA256 match; binary audit re-run on the fresh wheel (marker 0).
3. No new tracker comment posted — no material new fact (P15 rule: no comment without a new finding).
