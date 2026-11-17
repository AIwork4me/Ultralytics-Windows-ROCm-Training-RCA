# P18 BASELINE — Windows RX 7900 XTX (gfx1100) Second-Architecture PR Validation

**Mission**: P18 · **Date**: 2026-11-15 · **Scope**: Ultralytics PR #27198 + #27203 physical-GPU validation on the SECOND architecture (gfx1100), complementing P17 gfx1151 evidence.

## 1. Frozen PR heads (verified live via `gh pr view` at 2026-11-15 ~15:05+08:00)

| PR | Branch | HEAD SHA | State | Commits |
|---|---|---|---|---|
| #27198 check_amp probe guard | `checkamp-guard-probe-exceptions` | `e5ac8593db60880b92b3e3cbd2e11ee3a7344034` | OPEN / MERGEABLE | 8 |
| #27203 HIP device gates | `checkamp-gpu-gates-hip-fallback` | `563ff46e0c3347cc68db420e1b268a22a456e317` | OPEN / MERGEABLE | 11 |

Both reference SHAs were still the live heads — no delta re-review was required. CI at head: all green for both, incl. `Tests (windows-latest, 3.13, latest): success`.

## 2. Environment (full freeze: `evidence/raw/p18/P18_ENVIRONMENT_AND_PROVENANCE.json`)

- **GPU**: AMD Radeon RX 7900 XTX · `gcnArchName=gfx1100` · 48 CUs · 24 GB (runtime 25,753,026,560 bytes; WMI `AdapterRAM` 4 GB is the known 32-bit cap, runtime data governs)
- **OS**: Windows 11 build 26300 · **Driver**: 32.0.21030.2001
- **Python**: CPython 3.12.16, venv `python -m venv --copies` at `C:\P18\venv`
- **Torch stack** (source `https://repo.amd.com/rocm/whl-multi-arch/`): torch 2.12.0+rocm7.14.1 (hip 7.14.60850), torchvision 0.27.0+rocm7.14.1, torchaudio 2.11.0+rocm7.14.1, amd-torch-device-gfx1100 **and** amd-torch-device-gfx110x (family wheel — split-wheel trap satisfied), amd-torchvision-device-gfx1100, rocm-sdk-* 7.14.1
- **MIOpen**: process-loaded `...\site-packages\_rocm_sdk_libraries\bin\miopen.dll`, SHA256 `e97891df7ea0ba2b6eda703bd69499521dc9a38300fe626f412b5544dec647bc`; upstream fix ROCm/rocm-libraries#13437 NOT in any wheel → local ENGINEERING_REFERENCE shim (`HIPRTC_COMPILE_OPTIONS_APPEND=-I.../miopen_shims`, wheel bytes untouched), same mechanism as the Day1-verified environment
- **Ultralytics source under test**: per-PR git worktrees (`C:\P18\pr27198` @ e5ac8593, `C:\P18\pr27203` @ 563ff46e, `C:\P18\combined` @ upstream-main 3e59149d4 + both PRs merged), import isolation verified per-run via `ultralytics.__file__`

## 3. Official support matrix check

ROCm 10.1.0 compatibility matrix lists RX 7900 XTX (gfx1100) as supported on Windows 11 (Adrenalin 26.10.41.05 line). However the **official user Golden Path remains BLOCKED_RELEASE** (see P18_GFX1100_GOLDEN_PATH.md): the 10.1.0 runtime wheels still ship the MIOpen #13437 defect, and both PRs are unmerged. All P18 GPU validation therefore runs under the 7.14.1 stack as **ENGINEERING_REFERENCE**, never claimed as OFFICIAL_GOLDEN_PATH_PASS.

## 4. Environment incidents (recorded, not hidden)

1. **Smart App Control activated by KB5132688/KB5132061 (2026-11-13)** — blocked uv venv trampoline `python.exe`s and unsigned AMD DLLs (`hiprand.dll`, CodeIntegrity events 3033/3118; `WinError 4551`). Last good GPU day was 2026-11-07; this is a machine policy change, not environment corruption. Classification: ENVIRONMENT (policy). Resolution: user disabled SAC via Windows Security UI at ~15:5x (verified `VerifiedAndReputablePolicyState=0`); GPU stack functional again. Workaround used while blocked: base-CPython direct + `venv --copies`.
2. **github.com:443 intermittent outage** (~15:2x–16:0x+08:00): api.github.com and codeload.github.com stayed reachable; clone succeeded on retry. No mirror used.
3. **Split-wheel trap hit on the torchvision side**: `torch[device-gfx1100]` does NOT pull torchvision's device wheel — first AMP train crashed at `torchvision.ops.nms` with `hipErrorInvalidDeviceFunction` (log `phase_b3_train_amp.log` first attempt). Fixed by `torchvision[device-gfx1100]==0.27.0+rocm7.14.1` (amd-torchvision-device-gfx1100). Matches the P16-era trap documentation, now extended to torchvision.
4. Missing upstream runtime dep `polars` (new in ultralytics 8.4.2xx `read_results_csv`) — installed; recorded for future env builds.

## 5. Phase A — GPU basic correctness (log `phase_a_gpu_basic.log`, exit 0)

- A1 detection: available=True, count=1, name=AMD Radeon RX 7900 XTX, gfx1100, 23.98 GB, 48 SMs — PASS
- A2 memory: free 25,597,083,648 / total 25,753,026,560 (99.4% free) — PASS
- A3 math on device: FP32 matmul finite (187.5 ms incl. warmup), FP16 matmul finite (rel err 3.6e-4 vs FP32), FP32 & FP16 conv2d + backward finite grads, SGD optimizer step max|Δw|=5.6e-3 (params really changed) — PASS
- A4 runtime identity (psutil memory_maps of the live process): amdhip64_7.dll, hiprtc0714.dll, miopen.dll (SHA above), rocblas.dll, c10_hip.dll, torch_hip.dll — all from the P18 venv — PASS

**Phase A verdict: PASS.**
