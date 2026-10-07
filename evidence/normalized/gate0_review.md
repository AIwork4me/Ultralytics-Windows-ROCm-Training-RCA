# Gate 0 Review — Independent Environment Baseline Audit

Auditor: independent evidence auditor (challenge mode). Date: 2026-10-07.
All commands below were run by the auditor on the machine under test, read-only. Evidence files referenced live in `evidence\raw\environment\`.

Legend: **FACT** = directly observed by auditor (command + output) or present verbatim in an evidence file. **INFERENCE** = auditor's interpretation, explicitly reasoned.

---

## Verdict per question

### Q1. Is the machine really native Windows (not WSL)?

**VERDICT: PASS**

Auditor-run commands and outputs:

- `uname -a` → `MINGW64_NT-10.0-26200 DESKTOP-IF0424E 3.6.10-710e5275.x86_64 ... Msys` — **FACT**. MSYS2/Git Bash userland on Windows; a WSL session would report a `Linux ... microsoft-standard-WSL2` kernel.
- `cat /proc/version` → `MINGW64_NT-10.0-26200 version 3.6.10 ... (gcc version 15.3.0 (GCC))` — **FACT**. This is MSYS's emulated procfs; in WSL this file reads `Linux version <ver>-microsoft-standard-WSL2`.
- `ls /mnt/c` → does not exist; `WSL_DISTRO_NAME` / `WSL_INTEROP` empty — **FACT**. WSL-specific mounts/env absent.
- `powershell -NoProfile` → `[RuntimeInformation]::OSDescription` = `Microsoft Windows 10.0.26200`; `$PSVersionTable.PSVersion` = `5.1.26100.9444`; OS/Process architecture = `X64` — **FACT**.
- File `windows_os.txt`: `Microsoft Windows 11 家庭版 中文版`, Version 10.0.26200, BuildNumber 26200, 64-bit — **FACT**, matches live check.
- File `torch_probe.txt`: python `platform: Windows-11-10.0.26200-SP0`, CPython `MSC v.1942 64 bit (AMD64)` build — **FACT**.

Nuances the RCA must not get wrong:

- `wsl.exe -l -v` shows `Ubuntu2204  Stopped  2` — **FACT**: WSL *exists* on this machine but is stopped, and this session is not inside it. The RCA must scope all claims to the native-Windows context (it does: every probe targets `C:\Users\rocm\miniconda3\python.exe`).
- `Get-CimInstance Win32_ComputerSystem).Model` = `ProArt PX13 HN7306EA` — **FACT** (chassis model; recorded for completeness; WMI CPU/GPU names below are the authoritative silicon evidence).

### Q2. Is the GPU really Radeon 8060S / gfx1151?

**VERDICT: PASS**

Auditor-run command:

```
C:/Users/rocm/miniconda3/python.exe -c "import torch; p=torch.cuda.get_device_properties(0); print(p); ..."
```

Output — **FACT**:

```
_CudaDeviceProperties(name='AMD Radeon(TM) 8060S Graphics', major=11, minor=5,
gcnArchName='gfx1151', total_memory=80065MB, multi_processor_count=20,
uuid=30303030-3031-3936-3030-303030303030, L2_cache_size=2MB)
AMD Radeon(TM) 8060S Graphics
is_available: True
device_count: 1
```

- `major.minor=11.5` → gfx11 arch, and `gcnArchName='gfx1151'` states it explicitly — **FACT**. No interpretation needed beyond confirming consistency (11.5 ↔ 1151).
- WMI cross-check (auditor-run `Get-CimInstance Win32_VideoController`, identical to `gpu_wmi.txt`): `AMD Radeon(TM) 8060S Graphics`, DriverVersion `32.0.22032.6002`, `VideoProcessor: AMD Radeon Graphics Processor (0x1586)` — **FACT**.
- CPU (file `cpu.txt` + `torch_collect_env.txt`): `AMD RYZEN AI MAX+ 395 w/ Radeon 8060S`, 16C/32T — **FACT**. Consistent: 8060S is the Strix Halo (Ryzen AI MAX+ 395) iGPU.

Cross-check discrepancy, resolved (not a contradiction):

- WMI `AdapterRAM=4293918720` (~4 GiB) vs torch `total_memory=80065MB` (~78 GiB) — **FACT** both.
- **INFERENCE**: WMI's `AdapterRAM` is a 32-bit field that for APUs reports only the small BIOS-reserved carve-out, while HIP sees the full unified-memory allocation. Supporting **FACT**: auditor-measured total system RAM `132766306304` bytes (~124 GiB) makes an ~80 GiB GPU allocation plausible. File `torch_probe.txt` independently reports `total_memory=83954728960` (= 80065 MiB), matching my live probe bit-for-bit.

### Q3. Is this really ROCm PyTorch (not CPU/CUDA)?

**VERDICT: PASS**

Auditor-run command: `C:/Users/rocm/miniconda3/python.exe -c "import torch; print(torch.__version__, torch.version.hip, torch.version.cuda)"` (plus torchvision/torchaudio, see Q4).

Output — **FACT**: `2.12.0+rocm7.14.0` / `7.14.60850` / `None`.

- Version tag `+rocm7.14.0`, `torch.version.hip=7.14.60850`, `torch.version.cuda=None` — **FACT**. Not a CUDA build (cuda is None).
- Binary-level check (auditor): `ls .../torch/lib | grep -ic cuda` → `0`; the dir contains `torch_hip.dll`, `c10_hip.dll` — **FACT**. A CUDA build would carry `torch_cuda.dll`/`c10_cuda.dll`. Conclusive.
- Not CPU-only: auditor GPU smoke test `x = torch.rand(1024,1024,device='cuda'); (x@x).sum()` → `GPU matmul smoke test OK, result: 267784320.0` — **FACT**. GPU compute genuinely works.
- File corroboration: `torch_collect_env.txt` — "ROCM used to build PyTorch: 7.14.60850", "HIP runtime version: 7.14.60850", "MIOpen runtime version: 3.5.2", "GPU Models and configuration: AMD Radeon(TM) 8060S Graphics (gfx1151)" — **FACT**.

### Q4. Are torch, torchvision, and torchaudio all ROCm builds?

**VERDICT: PASS (with one minor note on torchaudio)**

Auditor-run output — **FACT**:

```
torch: 2.12.0+rocm7.14.0        (hip: 7.14.60850, cuda: None)
torchvision: 0.27.0+rocm7.14.0
torchaudio: 2.11.0+rocm7.14.0
ultralytics: 8.4.174
```

- All three version strings contain `+rocm7.14.0`; `import` of each succeeds from `C:\Users\rocm\miniconda3\python.exe` — **FACT**. Matches `torch_probe.txt` (lines 13, 27–28) and `pip_freeze.txt` (`torch==2.12.0+rocm7.14.0`, `torchvision==0.27.0+rocm7.14.0`, `torchaudio==2.11.0+rocm7.14.0`) — **FACT**.
- `site-packages` dist-info dirs exist for `torch-2.12.0+rocm7.14.0`, `torchvision-0.27.0+rocm7.14.0`, `torchaudio-2.11.0+rocm7.14.0`, plus `amd-torch-device-gfx1151`, `amd-torch-device-gfx11`, `amd-torchvision-device-gfx1151` device wheels — **FACT** (auditor `ls` of site-packages; consistent with `torch_probe.txt` metadata section).
- Note (minor, non-blocking): torchvision 0.27.0 is the expected pair for torch 2.12.0 under the historical offset convention; **torchaudio 2.11.0 alongside torch 2.12.0** breaks the usual torchaudio-major.minor == torch-major.minor convention. `pip check` does not flag it and it imports cleanly — **FACT**. **INFERENCE**: possibly intentional for this AMD ROCm wheel line; torchaudio is not on the ultralytics training path, so no RCA impact. Disclose only.

### Q5. Environment inconsistencies that could invalidate the RCA

**VERDICT: PASS with mandatory disclosures — and one decisive positive finding: the auditor REPRODUCED the RCA's failure class live.**

Reproduction (auditor-run, single python one-liner, no environment changes):

```
GPU matmul smoke test OK, result: 267784320.0
cudnn(miopen) version: 3005002
MIOpen(HIP): Error [Compile] 'hiprtcCompileProgram(...)' MIOpenBatchNormFwdTrainSpatial.cpp:
             HIPRTC_ERROR_COMPILATION (6)
... include\miopen_type_traits.hpp:151: fatal error: 'type_traits' file not found
MIOpen Error: ... hipoc_program.cpp:299: Code object build failed. Source: MIOpenBatchNormFwdTrainSpatial.cpp
RuntimeError: miopenStatusUnknownError
```

— **FACT**. Basic HIP compute works; MIOpen's runtime (HIPRTC) compilation of the BatchNorm training kernel fails because a standard C++ header (`<type_traits>`) cannot be found. The RCA's claimed failure (MIOpen/HIPRTC BatchNorm training failure) is real, current, and reproducible on this exact baseline. The full traceback lives in this audit's session log; the RCA should attach its own reproduction.

---

## Environment inconsistencies

### 1. Conda env `yolo_amd` is empty; working stack lives in `base`

- **FACT**: `conda list -n yolo_amd` returns zero packages; `C:\Users\rocm\miniconda3\envs\yolo_amd\python.exe` does not exist (dir contains only `conda-meta`, `etc`). Matches `conda_env_list.txt` (env listed) — the listing alone never proves an env is populated.
- **FACT**: `conda_info.txt` shows base writable, active environment None; all validated probes target `C:\Users\rocm\miniconda3\python.exe` (`torch_probe.txt` line 4).
- **ASSESSMENT**: Functionally acceptable for the RCA — `base` is a real writable conda env and it demonstrably contains the working ROCm stack. It is *not* acceptable to imply a clean dedicated environment. `base` carries heavy unrelated payload (paddlex, mineru_rocm / paddleocr_vl_rocm editable installs, onnxruntime-directml, three opencv variants), which widens the interference surface and harms reproducibility. **Plausibly causal for the MIOpen/HIPRTC BatchNorm failure? No** — the failure reproduces inside base with no third-party code on the stack trace; the traceback is pure torch→MIOpen→HIPRTC. But the RCA must pin every command to the absolute python path and disclose that `yolo_amd` is an empty husk.

### 2. Unset INCLUDE / LIB / HIP_PATH / ROCM_PATH

- **FACT**: `torch_probe.txt` env section shows `INCLUDE/LIB/LIBPATH/HIP_PATH/ROCM_PATH/CPATH/CPLUS_INCLUDE_PATH` all unset; auditor confirmed at Windows Machine and User scope via `[Environment]::GetEnvironmentVariable(...)` — all empty.
- **INFERENCE (important)**: unset `HIP_PATH`/`ROCM_PATH` per se is *expected and harmless* for the pip-wheel ROCm distribution model — the runtime is bundled in site-packages (`_rocm_sdk_core/bin/hiprtc0714.dll`, `_rocm_sdk_libraries/bin/MIOpen.dll`, `torch/lib/torch_hip.dll`; all observed — **FACT**) and torch demonstrably loads and executes GPU kernels. However, the **unset `INCLUDE` combined with no C++ standard library on the system is a leading root-cause candidate** for the reproduced failure:
  - `find` over `_rocm_sdk_core` and `_rocm_sdk_libraries`: **no `type_traits` anywhere** — **FACT**. The exact header HIPRTC fails to find is absent from the entire ROCm wheel tree.
  - The wheel *does* bundle clang resource headers (`_rocm_sdk_core/lib/llvm/lib/clang/23/include/stddef.h` — **FACT**), but a clang resource dir does not provide the C++ standard library headers MIOpen's kernels `#include`.
  - No MSVC installed: neither `C:\Program Files\Microsoft Visual Studio` nor `C:\Program Files (x86)\Microsoft Visual Studio` exists — **FACT**. So there is no MSVC STL to find either.
  - **INFERENCE chain**: MIOpen JIT-compiles `MIOpenBatchNormFwdTrainSpatial.cpp` → includes `<type_traits>` → HIPRTC has no C++ STL include path (wheel doesn't ship one; INCLUDE unset; no MSVC) → `HIPRTC_ERROR_COMPILATION (6)` → `miopenStatusUnknownError`. This is the RCA's primary hypothesis to confirm/refute.

### 3. Multiple virtual display adapters

- **FACT**: auditor WMI query (matches `gpu_wmi.txt`): `GameViewer Virtual Display Adapter` (driver 15.6.5.199, Status OK) alongside the AMD iGPU. Additionally `torch_probe.txt` PATH includes VisionMaster4.4.0 and MVS machine-vision runtime DLL directories.
- **ASSESSMENT**: Very unlikely to affect a MIOpen/HIPRTC BatchNorm failure. HIP sees exactly one device (`device_count: 1` — **FACT**); virtual display adapters do not register as HIP devices and are not on the kernel-compile path. Residual risk is driver-level hooking of graphics contexts by the remote-viewer software — speculation, low probability. **Disclose; not causal.**

### 4. Chinese-locale Windows

- **FACT**: `windows_os.txt` = "Windows 11 家庭版 中文版"; auditor `(Get-Culture).Name` = `zh-CN`.
- **ASSESSMENT**: Unlikely causal for this failure. The failing compile path is pure-ASCII (`C:\Users\rocm\AppData\Local\Temp\comgr-107328-7-b88ff7\...`, username `rocm`, TEMP path ASCII — **FACT**), and the error is a deterministic header-not-found, not an encoding/IO error. Note the mojibake in `torch_collect_env.txt` line 16 (`瀹跺涵鐗?涓枃鐗?`) is a UTF-8→GBK decode artifact of the capture script's logging, not an environment fault — **INFERENCE**. Disclose; not causal.

### 5. Pre-existing pip dependency conflicts (pydantic / ruamel-yaml / PyYAML)

- **FACT**: auditor re-ran `python -m pip check` → identical to `pip_check.txt`:
  - `anaconda-cli-base 0.8.2 has requirement pydantic>=2.12, but you have pydantic 2.9.0`
  - `conda 26.3.2 has requirement ruamel-yaml<0.19, ... you have ruamel-yaml 0.19.1`
  - `paddlex 3.7.2 has requirement PyYAML==6.0.2, but you have pyyaml 6.0.3`
- **ASSESSMENT**: None of these are on the BatchNorm GPU path. pydantic/ruamel affect conda/anaconda CLI tooling; PyYAML 6.0.3 vs 6.0.2 is a patch-level difference that ultralytics config parsing tolerates. **Cannot plausibly cause a HIPRTC kernel compilation failure.** Disclose as hygiene debt; non-causal.

### 6. Additional inconsistencies found by the auditor (not in the checklist)

- **Three coexisting opencv installs** — **FACT** (`pip_freeze.txt`): `opencv-python==5.0.0.93`, `opencv-contrib-python==4.10.0.84`, `opencv-python-headless==4.13.0.92`. Known to cause cv2 shadowing/duplicate-symbol issues in dataloaders; irrelevant to MIOpen kernel compile. Disclose.
- **Stray wheel files inside site-packages** — **FACT**: `numpy-2.1.0-cp313-cp313-win_amd64.whl` and `scipy-1.18.0-...whl` sit as files in `...\Lib\site-packages\`. Sign of manual install practices; inert for imports. Hygiene flag.
- **Editable installs polluting every python start in base** — **FACT**: `__editable__.mineru_rocm-1.0.0.pth` and `__editable__.paddleocr_vl_rocm-0.1.0.pth` in site-packages extend `sys.path` for every process, including training runs. Could shadow modules in principle; not plausibly related to HIPRTC. Disclose.
- **onnxruntime-directml==1.24.4 alongside onnxruntime==1.27.0** — **FACT** (`pip_freeze.txt`). A competing DirectML GPU stack exists on the box; only relevant if loaded into the same process; ultralytics training does not use it. Disclose.

---

## Overall assessment

**The baseline is VALID and does not invalidate the RCA — on the contrary, the auditor independently reproduced the RCA's central failure on this exact baseline.** Native Windows 11 (26200) with a genuine Ryzen AI MAX+ 395 / Radeon 8060S (gfx1151, confirmed by `gcnArchName` and WMI) running genuine pip-wheel ROCm PyTorch 2.12.0+rocm7.14.0 (+ matching torchvision/torchaudio) with Ultralytics 8.4.174 in conda `base`. GPU matmul executes; MIOpen BatchNorm training kernels fail at HIPRTC compile time with `'type_traits' file not found` → `HIPRTC_ERROR_COMPILATION (6)` → `miopenStatusUnknownError`.

For the RCA to stay valid it must:

1. Pin and state that ALL commands use `C:\Users\rocm\miniconda3\python.exe` (conda base), and explicitly disclose that `envs\yolo_amd` is empty and unused — never describe it as the test environment.
2. Lead the causal chain with the C++-standard-library gap: no `type_traits` anywhere in the ROCm wheel tree (auditor `find`), no MSVC installed, `INCLUDE` unset, while clang resource headers *are* bundled — this is the strongest evidenced root-cause candidate for the HIPRTC compile failure, and it makes "unset INCLUDE" potentially causal rather than cosmetic.
3. Treat unset `HIP_PATH`/`ROCM_PATH` as expected for the pip-wheel distribution model (runtime DLLs load from site-packages; GPU compute works) — do not present them as errors.
4. Disclose as non-causal hygiene factors: GameViewer virtual display adapter (plus VisionMaster/MVS DLL dirs on PATH), zh-CN locale (with the collect-env mojibake explained as a logging artifact), the three pip-check conflicts, triple opencv installs, stray wheels, and editable-install path pollution.
5. Not claim WSL anywhere (WSL exists on the machine — Ubuntu2204, stopped — but the tested stack is native Windows; the two must not be conflated), and explain the WMI AdapterRAM ~4 GiB figure as a 32-bit/carve-out reporting artifact versus the ~78 GiB HIP-visible unified allocation on a ~124 GiB RAM system.
