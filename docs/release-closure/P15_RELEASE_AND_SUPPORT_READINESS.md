# P15.10 — Release and User Support Readiness (2026-11-15)

Each condition requires explicit evidence. "Merged source" ≠ "released binary" ≠ "user-facing support".

| # | Condition | Status | Evidence / owner |
|---|---|---|---|
| A | MIOpen fix source merged | ✅ PASS | ROCm/rocm-libraries PR [#13437](https://github.com/ROCm/rocm-libraries/pull/13437) merge commit `f0a5d266` (2026-10-19); binary lineage proven in P13437/P14 missions |
| B | Windows SDK/wheel built with the fix | ❌ **BLOCKED_RELEASE** | no official Windows wheel post-dates the merge: whl-next `rocm_sdk_libraries-10.1.0` byte-identical to pre-fix build (Last-Modified 2026-10-05, size 118,645,973), all TheRock tags pre-merge — P15 live re-verification (`P15_OFFICIAL_RELEASE_CLOSURE.md`). Owner: AMD release chain |
| C | Official Windows package published (with fix) | ❌ BLOCKED_RELEASE | depends on B; both channels rescanned today |
| D | Correct official driver/architecture supported | ⚠️ PARTIAL | gfx1151 works with the current official wheels (real evidence); per-class official support matrix for a second class unverified (no hardware). Owner: AMD documentation + hardware availability |
| E | Ultralytics PR merged | ⏳ IN_PROGRESS | #27198 open (human review pending); #27203 open (new P15 defect: NVIDIA-only GPU gates). Owners: ultralytics maintainers |
| F | Official Ultralytics PyPI release contains the fixes | ❌ NOT_RELEASED | released 8.4.182/8.4.213 lack both changes; `publish.yml` gates on maintainer version bumps |
| G | Public installation documentation updated | ❌ PREPARED_NOT_SUBMITTED | upstream AMD docs are Linux-only today (verified); prepared content exists (`P15_OFFICIAL_WINDOWS_DOCS_READINESS.md`); submission deferred until claims match official-package reality (no overclaim rule) |
| H | Two GPU-class acceptance completed | ❌ BLOCKED_HARDWARE | gfx1151 PASS; second class unavailable (`P15_TWO_ARCH_WINDOWS_GPU_MATRIX.md`) |
| I | Independent user acceptance completed | ❌ BLOCKED_INDEPENDENT_USER_TEST | issue #14 zero response (verified today); kit ready (`P15_INDEPENDENT_USER_ACCEPTANCE.md`) |

## Support readiness for the current released stack

What a Windows Radeon user gets **today** from official channels: FP32 training works with the official wheel when host MSVC STL is present; AMP works on the official wheel (precheck + real updates, P9/P14/P15 evidence); the no-STL robustness gap remains until B/C clear. The golden-path kit documents exactly this boundary and rejects unsupported paths explicitly (CPU-only refusal, actionable dataset/checkpoint errors).

## Owner summary

| Blocker | Owner | Unblocking action |
|---|---|---|
| B/C fixed wheel | AMD release chain | publish post-merge Windows SDK/wheel |
| E merge | ultralytics maintainers | human review of #27198/#27203 |
| F release | ultralytics (version bump) | after E |
| G docs | ultralytics docs owner | PR after GATE 3 |
| H hardware | project owner | provide second class |
| I tester | independent developer | accept invitation / public call |
| Security (carried) | RCA owner | rotate ZHIPU_API_KEY (history still contains blobs) |
