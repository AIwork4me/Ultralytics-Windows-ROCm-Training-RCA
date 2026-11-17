# P15.1 — Official Release Closure (2026-11-15)

Verdict: **BLOCKED_RELEASE** (maintained; re-confirmed live today, no new wheel to validate).

## 1. Objective

Eliminate the no-STL MIOpen blocker from the ordinary Windows installation path by obtaining an official Windows wheel whose MIOpen contains merged PR [#13437](https://github.com/ROCm/rocm-libraries/pull/13437) (merge commit `f0a5d266`, 2026-10-19).

## 2. Live channel re-scan (2026-11-15)

Both official channels inspected (raw index HTML archived at `release-provenance/raw/p15_baseline/`):

| Channel | Newest Windows cp313 torch wheel | Change vs P14 |
|---|---|---|
| `stable.repo.amd.com/rocm/whl-next/` (→ `/rocm/pytorch/whl-next/`) | torch **2.14.0+rocm10.1.0** | none |
| `repo.amd.com/rocm/whl-multi-arch/` | torch **2.12.0+rocm7.14.1** | none |

## 3. Silent-rebuild check on the decisive artifact

`rocm_sdk_libraries-10.1.0-py3-none-win_amd64.whl`:

- Content-Length **118,645,973** — byte-identical to the P14-downloaded copy (SHA256 `0c34bafbb4aa626cc710d8b130bb314f591194c3d79eeb5892b755ea0be06159`).
- Last-Modified **Mon, 05 Oct 2026 09:19:46 GMT** — predates the #13437 merge date (2026-10-19).

⇒ Same S3 object as P14 audited; no rebuild. Its embedded MIOpen.dll (P14 immutable record): SHA256 `266d716b…c1429b4`, version string `3.6.1.39d8d603`, build commit `39d8d603` (2026-09-16) **< merge `f0a5d266`**, `miopen_initializer_list` marker 0 (post-fix reference = 2). Runtime legs from P14 (preserved): official-7.14.1 FAIL / whl-next-10.1.0 FAIL / merged-source PASS — identical HIPRTC `type_traits` failure signature on both official channels.

## 4. Cut-point analysis (carried; unchanged)

Every public TheRock release tag predates the merge (10.1.0 = 2026-09-25 etc.) — no release slice contains the fix. The missing cut point remains: **a post-2026-10-19 MIOpen → Windows SDK/wheel build → publish cycle**. Packaging owner: AMD/TheRock release chain (tracked in [#15862](https://github.com/ROCm/rocm-libraries/issues/15862); P14 evidence comment 6887740468 stands; **no new comment posted today** — no new material finding).

## 5. P15 actions taken

1. Re-verified both channels + decisive artifact identity (above).
2. Confirmed no duplicate-fix obligation: #13437 is merged; nothing to resubmit.
3. Kept the whl-next torch 2.13/2.14 stack readiness fact: the base installs and does real GPU compute on gfx1151 (P14); it becomes the ordinary path the moment a fixed SDK ships.
4. **Bonus upstream-readiness finding (new in P15)**: upstream `checks.cuda_device_count()`/`GPUInfo.select_idle_gpu()` are NVIDIA-only and silently disable `tests/test_cuda.py` on healthy AMD HIP hosts — fixed and submitted upstream as ultralytics PR [#27203](https://github.com/ultralytics/ultralytics/pull/27203) (gfx1151 SKIP→PASS proof). This is prerequisite work for AMD-adjacent CI once the wheel ships.

## 6. Required verdict

**BLOCKED_RELEASE.** OFFICIAL_WHEEL_READY conditions are not met: no obtainable official Windows package contains the fix; the no-STL negative control therefore still FAILs on both official channels and cannot honestly pass elsewhere.

## 7. What unblocks

1. AMD release chain publishes any official Windows wheel (either channel) built from a post-merge MIOpen.
2. P15 re-runs the full §5 checklist on the new artifact: version string/build-commit, marker count, no-STL BatchNorm negative control, positive primitives, YOLO train step, AMP, checkpoint.
3. GATE 3 then re-verdicts automatically against recorded criteria.
