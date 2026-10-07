# Environment Baseline (Phase 0)

Captured: 2026-10-07 (UTC+8). All facts below are backed by raw logs in
`evidence/raw/environment/`.

## Operating system

| Item | Value | Evidence |
|---|---|---|
| Edition | Microsoft Windows 11 家庭版 中文版 (Home, Chinese) | `windows_os.txt` |
| Version / build | 10.0.26200 (build 26200), 64-bit | `windows_os.txt` |
| Kernel line (Python) | Windows-11-10.0.26200-SP0 | `torch_probe.txt` |

Native Windows, not WSL: Python platform string reports Windows (a WSL guest
would report `Linux`), and the failure involves Windows `*.dll` components.

## CPU

| Item | Value | Evidence |
|---|---|---|
| Name (WMI) | AMD RYZEN AI MAX+ 395 w/ Radeon 8060S | `cpu.txt` |
| Cores / threads | 16 / 32 | `cpu.txt` |

Note: WMI reports "RYZEN AI MAX+ 395" without the "PRO" token used in the task
briefing; this is the same APU (Radeon 8060S iGPU, gfx1151).

## GPU

| Item | Value | Evidence |
|---|---|---|
| Name | AMD Radeon(TM) 8060S Graphics | `gpu_wmi.txt`, `torch_probe.txt` |
| Windows display driver | 32.0.22032.6002 | `gpu_wmi.txt` |
| WMI AdapterRAM | 4,293,918,720 B (32-bit WMI field; not meaningful for unified memory) | `gpu_wmi.txt` |
| HIP device memory | 83,954,728,960 B (~80 GiB unified) | `torch_probe.txt` |
| Compute units | 20 | `torch_probe.txt` (`multi_processor_count`) |
| gfx target | major.minor = 11.5 → **gfx1151** | `torch_probe.txt`, `torch_collect_env.txt` |
| VideoProcessor PCI id | 0x1586 | `gpu_wmi.txt` |

A second, virtual adapter ("GameViewer Virtual Display Adapter", driver
15.6.5.199) exists; torch `device_count()==1` sees only the Radeon.

## Python / conda

| Item | Value | Evidence |
|---|---|---|
| Working interpreter | `C:\Users\rocm\miniconda3\python.exe` (base env) | `torch_probe.txt` |
| Python | 3.13.13 (Anaconda build, MSC v.1942) | `torch_probe.txt` |
| conda | 26.3.2 | `conda_info.txt` |
| Conda envs | `base`, `yolo_amd` | `conda_env_list.txt` |

### OBSERVATION — `yolo_amd` environment naming

The task briefing refers to "the existing yolo_amd environment". On this
machine the conda env named `yolo_amd` (created 2026-10-07 09:12 UTC+8 via
`conda create -n yolo_amd`) contains **no Python and no packages** — only
`conda-meta/` and `etc/` (its `conda-meta/history` shows zero install
transactions). The validated ROCm/PyTorch/Ultralytics stack that matches the
briefing's version matrix exactly is installed in the **base** environment
(`C:\Users\rocm\miniconda3`, all AMD/ROCm wheels installed via pip into
`Lib\site-packages`). All RCA experiments therefore use
`C:\Users\rocm\miniconda3\python.exe`. This discrepancy is recorded, not
modified.

## Software stack (validated working versions)

| Package | Version | Evidence |
|---|---|---|
| torch | 2.12.0+rocm7.14.0 (git 13eab2b3) | `torch_probe.txt` |
| torchvision | 0.27.0+rocm7.14.0 | `torch_probe.txt` |
| torchaudio | 2.11.0+rocm7.14.0 | `torch_probe.txt` |
| ultralytics | 8.4.174 | `torch_probe.txt` |
| ultralytics-thop | 2.2.2 | `torch_probe.txt` |
| rocm | 7.14.0 | `pip_freeze.txt` |
| rocm-bootstrap | 0.1.0 | `pip_freeze.txt` |
| rocm-sdk-core | 7.14.0 | `pip_freeze.txt` |
| rocm-sdk-libraries | 7.14.0 | `pip_freeze.txt` |
| rocm-sdk-device-gfx1151 | 7.14.0 | `pip_freeze.txt` |
| amd-torch-device-gfx1151 | 2.12.0+rocm7.14.0 | `pip_freeze.txt` |
| amd-torch-device-gfx11 | 2.12.0+rocm7.14.0 | `pip_freeze.txt` |
| amd-torchvision-device-gfx1151 | 0.27.0+rocm7.14.0 | `pip_freeze.txt` |
| HIP runtime | 7.14.60850 | `torch_collect_env.txt` |
| MIOpen runtime | 3.5.2 | `torch_collect_env.txt` |

All AMD/ROCm packages live in `C:\Users\rocm\miniconda3\Lib\site-packages`
(wheel-based install, not a system ROCm).

## Torch runtime probe

| Probe | Result |
|---|---|
| `torch.cuda.is_available()` | True |
| `torch.cuda.device_count()` | 1 |
| `torch.cuda.get_device_name(0)` | AMD Radeon(TM) 8060S Graphics |
| `torch.version.hip` | 7.14.60850 (non-null ⇒ ROCm build) |
| `torch.version.cuda` | None |
| `torch.backends.cudnn.enabled` | True |
| `torch.backends.cudnn.is_available()` | True (MIOpen-backed on ROCm) |
| `torch.backends.cudnn.version()` | 3005002 |

## Toolchain-relevant environment variables (normal shell)

`INCLUDE`, `LIB`, `LIBPATH`, `HIP_PATH`, `ROCM_PATH`, `CPATH`,
`CPLUS_INCLUDE_PATH`, `HIP_VISIBLE_DEVICES`, `ROCR_VISIBLE_DEVICES` are all
**unset**. `TEMP`/`TMP` = `C:\Users\rocm\AppData\Local\Temp`. Full sanitized
PATH (47 entries) in `torch_probe.txt`.

## Pre-existing dependency conflicts (recorded, not modified)

`pip check` (`pip_check.txt`, exit 1) reports three unrelated conflicts:

- `anaconda-cli-base 0.8.2` requires `pydantic>=2.12`, installed 2.9.0
- `conda 26.3.2` requires `ruamel-yaml<0.19`, installed 0.19.1
- `paddlex 3.7.2` requires `PyYAML==6.0.2`, installed 6.0.3

These match the briefing's note about pre-existing Conda/PaddleX conflicts.
No evidence in this RCA links them to the ROCm training failure; none were
modified.

## ROCm wheel layout & DLL provenance (Phase 10)

The ROCm stack is entirely wheel-installed into site-packages (no system
ROCm):

| Component | Physical location | SHA256 (prefix) |
|---|---|---|
| MIOpen.dll (492 MB, embeds HIPRTC kernel sources) | `...\site-packages\_rocm_sdk_libraries\bin\MIOpen.dll` | `74b4ee038803606e…` |
| MIOpenCKGroupedConv_gfx1151.dll | `_rocm_sdk_libraries\bin\` | `f67654a630cd5409…` |
| miopen_plugin.dll (hipdnn) | `_rocm_sdk_libraries\bin\hipdnn_plugins\engines\` | `fd9629078d8937e1…` |
| amdhip64_7.dll (HIP runtime) | `...\site-packages\_rocm_sdk_core\bin\` | `b4b4799f5deafb81…` |
| amd_comgr.dll | `_rocm_sdk_core\bin\` | `0a890dbdcd12e6a1…` |
| hiprtc0714.dll (HIPRTC) | `_rocm_sdk_core\bin\` | `c6159dd12714eed4…` |
| hiprtc-builtins0714.dll | `_rocm_sdk_core\bin\` | `33ae08201842711b…` |

A live torch process loads all of: `MIOpen.dll`, `hiprtc0714.dll`,
`amd_comgr.dll`, `amdhip64_7.dll`, `torch_hip.dll`, `c10_hip.dll` (47
ROCm-related modules total). The wheel also ships a bundled LLVM/clang at
`_rocm_sdk_core\lib\llvm\bin\amdclang.exe` — version string "AMD clang
version 23.0.0git", **Target: x86_64-pc-windows-msvc** — with a clang
resource `include` dir but **no C++ standard library** anywhere in the wheel
trees. Full data: `evidence/raw/environment/dll_provenance.json` /
`.txt`.

## Reproduce

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\00_capture_environment.ps1
```
