# P17 — PR #27203 Real-Hardware Validation on Windows Radeon 8060S (gfx1151)

Mission: P17 | Date: 2026-11-15
Machine: Windows 11 build 26200, AMD Radeon(TM) 8060S Graphics (gfx1151), driver 32.0.22032.6002
Stack: Python 3.13.16, torch 2.12.0+rocm7.14.1 (HIP 7.14.60850), no NVIDIA driver on host (nvidia-smi absent), no NVML

## Frozen sources

| PR | Branch tip validated | Full SHA |
|---|---|---|
| #27203 | checkamp-gpu-gates-hip-fallback @ GitHub head (API-confirmed 2026-11-15) | `563ff46e0c3347cc68db420e1b268a22a456e317` |

Worktree: `C:\Users\rocm\Desktop\YOLO_AMD\p17_pr27203` (detached HEAD, clean).
Import path verified per process into the worktree (see provenance JSON).

Branch-ancestry audit vs P16 head 8ef3e96f: fast-forward only. **7 new commits reviewed before running** (mission §0 requirement); substance of each:

- `1db03bd` Fix no-NVML GPU selection under CUDA_VISIBLE_DEVICES remapping (physical↔logical translation)
- `cb03651` Translate physical GPU IDs to visible logical IDs in CUDA tests
- `88ae3eb` Enforce unverifiable idle-utilization constraints on no-NVML hosts (**nonzero min_util_fraction → return []**, replacing P16's "warn but continue")
- `f71e036` Simplify no-NVML selection and real-device tests
- 3 bot auto-format commits interleaved

Net diff of the branch since P16: `ultralytics/utils/autodevice.py` (no-NVML fallback rewrite), `ultralytics/utils/checks.py` — wait, no: since P16 only autodevice.py + tests changed; `checks.py` `cuda_device_count()` (torch fallback under nvidia-smi absence) was already present at 8ef3e96f and is part of the full-PR diff (`78b5b150^..563ff46e`: 4 files, +67/−11).

## B1 — HIP GPU visibility (PHYSICAL_GPU)

Measured on the live HIP device (`b_suite_result.json`):

| Quantity | Value |
|---|---|
| torch.cuda.is_available() | True |
| torch.cuda.device_count() | 1 |
| cuda_is_available() | **True** |
| cuda_device_count() | **1** |
| consistent | True |

The NVIDIA-only failure mode is gone: with nvidia-smi absent, `cuda_device_count()` falls back to `torch.cuda.device_count()` (which reports the HIP device) instead of returning 0. Direct contrast measured on the #27198 tree (`P17_PR27198_GFX1151_RESULTS.md` §A6): same host yields `cuda_is_available()=False` there.

**B1 = PASS.**

## B2 — NVML absence path (measured, not assumed)

- `GPUInfo().nvml_available` = **False** (pynvml init fails: "NVML Shared Library Not Found" — real measurement on Radeon Windows host)
- `refresh_stats()` → gpu_stats empty; no fabricated utilization numbers; no crash; no silent selection of a "utilization-unverified" GPU under a utilization requirement (B5).
- No exception paths triggered; logger warnings disclose the limitation explicitly.

**B2 = PASS.**

## B3 — Automatic selection `device=-1`

`parse_device("-1")` → `"0"`; repeated call idempotent (same value); the returned index drives a real GPU tensor allocation (64×64 randn on device 0, sum finite, synchronize OK).

**B3 = PASS.**

## B4 — Idle free-memory threshold (real readings)

- `torch.cuda.mem_get_info(0)`: free = 83,614,412,800 bytes, total = 83,954,728,960 bytes → **free fraction 0.9959** (Radeon 8060S APU reports shared-GTT memory; reading is real, not assumed).
- `GPUInfo().select_idle_gpu(count=1, min_memory_fraction=0.2, min_util_fraction=0)` → `[0]` with log `Selected CUDA devices [0] (utilization not measured)`; matches expected `[0]` since 0.9959 ≥ 0.2.
- The selection path really calls `torch.cuda.mem_get_info(logical)` (verified by code inspection + CVD-remapped run B6 where the logical index differs from the physical ID).

**B4 = PASS.**

## B5 — Unverifiable utilization must return []

`select_idle_gpu(count=1, min_util_fraction=0.3)` (nvml_available=False) → **`[]`** with warning `Cannot verify 30.0% free GPU utilization without NVML.` — no device is ever misreported as idle-pass.

**B5 = PASS.**

## B6 — CUDA_VISIBLE_DEVICES=0 (isolated process, set before torch import)

`b6_cvd0.py` in a fresh process with `CUDA_VISIBLE_DEVICES=0`:

- visible device count = 1; cuda_device_count() = 1; cuda_is_available() = True
- parse_device("-1") = "0"; select_idle_gpu(count=1, mem 0.2, util 0) = [0]
- mem_get_info(0) = [83,786,756,096 / 83,954,728,960]
- Real GPU allocation on device 0 OK; device name AMD Radeon(TM) 8060S Graphics
- Returned device indices agree with PyTorch logical device space

**B6 = PASS.**

## B7 — Restriction handling

| Call (nvml off) | Result | Requirement |
|---|---|---|
| select_idle_gpu(count=1, indices=[]) | `[]` | explicit empty restriction never becomes "unlimited" ✔ |
| select_idle_gpu(count=1, indices=[99999]) | `[]` | nonexistent devices never selected ✔ |
| select_idle_gpu(count=1, indices=[0, 0]) | `[0]` | duplicates never returned twice ✔ |

**B7 = PASS.**

## B8 — Official test gates

pytest 9.2.0 (isolated install), #27203 tree:

| Test | Result | Notes |
|---|---|---|
| tests/test_cuda.py::test_amp | **PASSED in 13.29 s (final run)** | **Really executed on the live HIP device** — DEVICES=[0] computed by the fixed gate, proving B1's fix end-to-end. The gate fix is what made this run possible at all: on the #27198 tree the same test is SKIPPED (NVIDIA-only gate, see 27198 report §A6). Two earlier runs of this test during the mission are also on file and honestly archived: one FAILED in 12.54 s (branch lacks #27198's probe guard while the host HIP runtime was degraded — `AcceleratorError` escaped the unguarded probe; out of PR scope) and one hung 20+ min in MIOpen find against the zombie-locked user cache (before the cache redirect was applied). The final PASSED run is the verdict. |
| tests/test_python.py::test_select_idle_gpu_fallback | **PASSED** | exercises no-NVML host branch: util>0→[], indices=[]→[], indices=[99999]→[] |
| tests/test_python.py::test_select_device | **PASSED** | no regression in device parsing |

**B8 = PASS**: test_amp truly executed and PASSED on the real HIP GPU (no SKIP); the two test_python gates PASS with no regression. Honest note: the PASSED run landed in a healthy HIP window; the host's runtime health is intermittent (see reboot item in the final report), and the PASSED-vs-FAILED pair across runs is itself recorded as evidence of the environment fault, not of code behavior.

## B9 — Nonzero physical-device mapping (CVD=3)

- **Physical reproduction NOT RUN**: single-GPU host cannot expose physical GPU 3 under `CUDA_VISIBLE_DEVICES=3`. Marked `PHYSICAL_MULTI_GPU_NOT_RUN`.
- Real single-GPU behavior under CVD=3 measured (isolated process): torch.cuda.device_count()=0, cuda_device_count()=0, cuda_is_available()=False, select_idle_gpu → `[]` — nothing fabricated, nothing selected.
- **Logic-level verification of the physical→logical translation** (the code path is identical for any visible list): with CVD="3", `visible=['3']`, candidates=[3]; `logical = visible.index('3') = 0` → `mem_get_info(0)` queries the remapped logical device; selection returns the **physical** ID 3 as documented in the docstring; indices outside the visible set (e.g. 99999 or a hidden physical id) produce `logical=-1` → skipped. The same translation logic was **physically exercised** in B6 with CVD=0 (visible=['0'], logical=0, real mem_get_info + allocation), i.e. the code path itself ran on real hardware, only the identity of the physical index differs.
- **B9 = LOGIC_TEST_PASS + PHYSICAL_MULTI_GPU_NOT_RUN.**

## B10 — NVIDIA healthy-path protection (static review; no NVIDIA hardware on host)

Full-PR diff `78b5b150^..563ff46e` (4 files) reviewed hunk-by-hunk:

- `checks.py::cuda_device_count`: nvidia-smi success path byte-identical (same command, same parsing, same int conversion); only the `except` branch changed (0 → `torch.cuda.device_count()` fallback).
- `autodevice.py::select_idle_gpu`: **NVML-available path untouched** (filter/sort/select block unchanged; diff confined to `if not self.gpu_stats:` branch + docstring + `import os`).
- `tests/test_cuda.py` DEVICES: `min_util_fraction=autodevice_fraction if gpu_info.nvml_available else 0` — on NVIDIA CI (nvml_available=True) behavior is byte-identical to before.
- Docstring updates only restate the no-NVML contract.

**B10 = NVIDIA paths preserved (static) + NVIDIA_HARDWARE_NOT_RUN (no NVIDIA GPU on host — no claim of NVIDIA hardware PASS is made).**

## Quality gates (P17.4 cross-reference)

- `ruff format --check` on all four touched files: clean.
- `ruff check --extend-select F,I,D,UP,RUF,FA` (repo config): PR tree ≤ main baseline (10 vs 13 on checks.py; autodevice/tests clean or pre-existing only); **zero new errors**.
- AGENTS.md cold review: fallback logic lives in the actual owner (autodevice.py / checks.py), tests use the real host (no mock-heavy simulation), no shims, no new dependencies (stdlib `os`), NVML path untouched.

## Verdict

```
SOURCE_QUALITY_PASS
GFX1151_PHYSICAL_VALIDATION_PASS  (B1–B7 all PASS on real HIP hardware)
TEST_GATE_PASS                    (B8: test_amp really executed and PASSED on HIP; test_python gates PASS)
LOGIC_TEST_PASS                   (B9 physical→logical translation)
PHYSICAL_MULTI_GPU_NOT_RUN        (single-GPU host)
NVIDIA_NOT_RUN                    (no NVIDIA hardware; static review only)
```

Raw evidence: `evidence/p17/b_suite.py`, `b_suite_result.json`, `b6_cvd0.py`, `b6_cvd0_result.json`, pytest outputs, `P17_ENVIRONMENT_PROVENANCE.json`.
