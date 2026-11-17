# P16 BASELINE — Frozen Remote & Local State (2026-11-15)

Mission P16 start-of-work baseline. All values fetched live via GitHub API (`gh`), not assumed from prior phases.

## 1. Upstream Ultralytics PRs

| PR | State | Head | Mergeable | CI (check-runs at P16 start) | Last upstream activity |
|----|-------|------|-----------|------------------------------|------------------------|
| [#27198](https://github.com/ultralytics/ultralytics/pull/27198) (check_amp probe exceptions) | OPEN, not merged | `fc72b4eb85d654e3268a5bee1bc4beebc8704b13` | true | 15 success / 6 skipped / 0 failed | updated 2026-11-15T03:13:49Z |
| [#27203](https://github.com/ultralytics/ultralytics/pull/27203) (AMD HIP GPU detection) | OPEN, not merged | `a1be04841a38526652d7e117a1993eebe924049f` | true | 15 success / 6 skipped / 0 failed | updated 2026-11-15T04:12:50Z |

Review-thread state at P16 start:

- #27198: one UltralyticsAssistant review (2026-11-14T17:07Z, "construction/transfer can still crash") — already addressed at current head (guard now wraps construction + `.to(device)` + hooks + forward; reply posted at 23:51Z). No human review yet. CLA signed (bot ✅ 2026-11-14T17:06Z).
- #27203: one UltralyticsAssistant review (2026-11-15T03:12Z, empty-`indices` restriction bug) — fixed at `a1be048` (2026-11-15T03:28Z reply). No human review yet. CLA signed (bot ✅, "I have read the CLA Document…" comment 04:12Z).

## 2. Issue / tracker state

- [rocm-libraries #15862](https://github.com/ROCm/rocm-libraries/issues/15862) (Windows release tracker): OPEN, 2 comments (both ours, 2026-11-14/15). **No maintainer response.**
- [RCA issue #14](https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/issues/14) (independent developer invitation @LZ-QWQ): OPEN, **0 comments** — tester has not responded.

## 3. Official wheel channels (fresh scan 2026-11-15, see P16_OFFICIAL_WHEEL_BINARY_AUDIT)

- `repo.amd.com/rocm/whl-multi-arch/torch/` newest cp313 Windows wheel: `torch-2.12.0+rocm7.14.1` — **unchanged** since P15 scan.
- `stable.repo.amd.com/rocm/whl-next/` (TheRock-style layout: `rocm-sdk-core`, `rocm-sdk-libraries`, per-arch `amd-torch-device-gfx*`): newest = `rocm_sdk_core-10.1.0` / `torch-2.14.0+rocm10.1.0` / `amd_torch_device_gfx1151-2.14.0+rocm10.1.0` — **no 10.2.0, no new fixed artifact**.
- `rocm_sdk_libraries-10.1.0-py3-none-win_amd64.whl` re-downloaded 2026-11-15: SHA256 `0c34bafbb4aa626cc710d8b130bb314f591194c3d79eeb5892b755ea0be06159` — **byte-identical** to the P15-audited copy (Last-Modified 2026-10-05, predates audits). P15 PRE-FIX verdict carries over cryptographically.

## 4. RCA repository

- Branch `work/windows-rocm-training-release-closure` local = origin-tracking `e3188a67a202b7f1d1aa824b00cab31143ba9c87` (live `gh` check of the branch head confirmed same SHA at P16 start).
- Local clone has untracked `bus.jpg` (leftover test asset, ignored).

## 5. Local validation environment (gfx1151 host)

- Host: AMD Radeon 8060S (gfx1151 iGPU), Windows 11 build 26200.
- `p16_testenv` venv (created for P16, `--system-site-packages` over conda env `pm13437_merged`): torch 2.12.0+rocm7.14.1 (HIP, `torch.cuda.is_available()=True`), pytest 9.2.0, ruff 0.17.5 (upstream ruleset subset E4/E7/E9/F used; ruff 0.17.5's defaults include BLE001/S110 which upstream CI's pinned Actions ruff does not enforce — the same patterns exist throughout upstream code).
- `pynvml` importable but `nvmlInit()` fails on this host ("NVML Shared Library Not Found") → `GPUInfo().nvml_available=False` — the real no-NVML condition AMD Windows users have; local runs therefore exercise the PR #27203 fallback for real.
- `torch.cuda.mem_get_info(0)` on HIP: free/total = 83,786,756,096 / 83,954,728,960 = 0.9980 (idle iGPU).

## 6. Worktrees (AGENTS.md-compliant)

- `C:\Users\rocm\Desktop\YOLO_AMD\upstream_ultralytics` — branch `checkamp-guard-probe-exceptions` @ `fc72b4e` (PR #27198 head).
- `C:\Users\rocm\Desktop\YOLO_AMD\p16_pr27203` — branch `checkamp-gpu-gates-hip-fallback` @ `a1be048` (PR #27203 head; P16 corrections committed on top).

## 7. GitHub transport note

During P16, git-over-HTTPS to github.com was intermittently unusable (`Could not resolve host` / `Connection was reset` / connect timeouts) while the GitHub REST API (gh CLI) remained reachable. The P16 #27203 correction was therefore pushed via the Git Data API (blobs → tree → commit → ref update with `force=false`, i.e. a true fast-forward). Local branch resync deferred until transport recovers.
