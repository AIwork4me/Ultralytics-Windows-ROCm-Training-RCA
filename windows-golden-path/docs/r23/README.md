# Train Ultralytics YOLO on Windows with AMD Radeon — DRAFT (R23)

> **STATUS: R23_DRAFT_READY — NOT release-qualified.**
> As of 2026-11-15 **no official STABLE Windows ROCm package contains the
> MIOpen fix** (rocm-libraries #13437 / #15862). On machines without Visual
> Studio Build Tools, training fails at the first BatchNorm with
> `HIPRTC_ERROR_COMPILATION: 'type_traits' file not found`. This guide is
> publishable only after R22 OFFICIAL_STABLE_PASS. The commands below are
> REAL and were verified on an RX 7900 XTX machine — the blocker is the
> package content, not the commands.
>
> **FAIL-CLOSED quickstart (R21.1 TASK E):** `quickstart.ps1` now defaults to
> `-Mode Status` — it prints the gate status, installs nothing, and exits 3.
> The install-and-train flow runs only under the explicitly labeled
> `-Mode EngineeringDemonstration` (pre-fix stack; the #3956 failure without
> VS Build Tools is the expected demo result). `-Mode OfficialStable` is
> refused (exit 4) until R22 issues OFFICIAL_STABLE_PASS.

## What you need

| Item | Requirement |
|---|---|
| GPU | Radeon RX 7900 XTX (gfx1100) or Radeon 8060S (gfx1151) — tested archs |
| OS | Windows 11, AMD Adrenalin driver (tested 32.0.21030.2001) |
| Python | 3.12 or 3.13 (clean venv; no conda required) |
| Disk | ~8 GB (wheels + datasets + checkpoints) |

## Install (verified commands — gfx1100)

```powershell
# 1. clean venv
python -m venv C:\YOLO\venv
C:\YOLO\venv\Scripts\Activate.ps1

# 2. official AMD PyTorch stack (torch 2.12.0+rocm7.14.1 + device wheels)
python -m pip install torch torchvision `
    --index-url https://repo.amd.com/rocm/whl-multi-arch/
python -m pip install amd-torch-device-gfx1100 amd-torch-device-gfx110x `
    amd-torchvision-device-gfx1100 `
    --index-url https://repo.amd.com/rocm/whl-multi-arch/

# 3. Ultralytics (released wheel; 8.4.214 carries the AMD device-detection fix)
python -m pip install ultralytics==8.4.214

# 4. verify the GPU is really visible (rejects CPU-only installs)
python C:\path\to\harness\scripts\verify_environment.py   # or: yolo checks
```

For **gfx1151** replace the device wheels with
`amd-torch-device-gfx1151 amd-torchvision-device-gfx1151`
(everything else is identical).

⚠️ **Both** the per-arch wheel **and** the family wheel matter:
- missing `amd-torch-device-gfx110x` → silent SDPA corruption
- missing `amd-torchvision-device-gfx1100` → `torchvision.ops.nms`
  `hipErrorInvalidDeviceFunction`

## Train

```powershell
yolo train model=yolo26n.pt data=coco8.yaml epochs=1 device=-1
```

`device=-1` auto-selects your Radeon GPU (8.4.214 fixed this on AMD).
Expected output: [expected-cli-output.txt](expected-cli-output.txt).

## After training

- Checkpoints: `runs\detect\train\weights\best.pt` (best) and `last.pt` (latest)
- Inference: `yolo predict model=runs\detect\train\weights\best.pt source=your.jpg device=-1`
- Resume an interrupted run: `yolo train resume runs\detect\train\weights\last.pt`
  (needs the interrupted run's `last.pt`; a finished run's `last.pt` is not
  resumable training state)

## Known blocker (the honest part)

The official MIOpen.dll in every **stable** Windows wheel still requires host
MSVC STL headers at runtime (issue #15862). If you have Visual Studio Build
Tools installed, training works TODAY with the commands above. Without them,
first BatchNorm fails. The fix is merged upstream and already ships in dev /
nightly channel libraries — the stable cut is the release event this project
is waiting for. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

We do NOT support MIOpen.dll replacement as a user path. No promises on
NVIDIA-equal speed, TensorRT, or ONNX-runtime CUDA-EP on AMD.
