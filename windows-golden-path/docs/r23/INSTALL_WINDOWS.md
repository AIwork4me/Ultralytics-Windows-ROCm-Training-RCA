# INSTALL_WINDOWS.md (R23 draft — verified 2026-11-15 on gfx1100)

Step-by-step for a beginner. Commands are the exact ones validated by the
R21 harness run (evidence: `evidence/raw/r21/`).

> **READ FIRST (R21.1 TASK E):** the stack documented below is the
> ENGINEERING-REFERENCE (pre-#13437) stack. Following these steps is an
> **engineering demonstration**, not a supported no-workaround install: without
> Visual Studio Build Tools on this machine, training fails at the first
> BatchNorm (issue #3956). `quickstart.ps1` therefore defaults to a fail-closed
> status mode — use `-Mode EngineeringDemonstration` to run this flow.

## 1. Check your GPU

- RX 7900 XTX → gfx1100 path (this page)
- Radeon 8060S → gfx1151: identical steps, different device wheels (§3)
- Untested archs: not covered, no claims made

## 2. Check Windows + driver

- Windows 11 (tested build 26300)
- AMD Adrenalin driver — tested 32.0.21030.2001; install the latest from amd.com
- PowerShell: `Get-CimInstance Win32_VideoController | ? Name -match 'Radeon'`

## 3. Python + packages

```powershell
# Python 3.12 or 3.13 from python.org, then:
python -m venv C:\YOLO\venv
C:\YOLO\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip

# gfx1100 (RX 7900 XTX) — official AMD index:
python -m pip install torch==2.12.0+rocm7.14.1 torchvision==0.27.0+rocm7.14.1 `
    --index-url https://repo.amd.com/rocm/whl-multi-arch/
python -m pip install `
    amd-torch-device-gfx1100==2.12.0+rocm7.14.1 `
    amd-torch-device-gfx110x==2.12.0+rocm7.14.1 `
    amd-torchvision-device-gfx1100==0.27.0+rocm7.14.1 `
    --index-url https://repo.amd.com/rocm/whl-multi-arch/

# gfx1151 (Radeon 8060S) — only the device-wheel line differs:
#   amd-torch-device-gfx1151==2.12.0+rocm7.14.1
#   amd-torchvision-device-gfx1151==0.27.0+rocm7.14.1

# Ultralytics (released wheel)
python -m pip install ultralytics==8.4.214
```

## 4. Verify GPU detection

```powershell
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# True AMD Radeon RX 7900 XTX
```

If `False`: you got a CPU torch wheel — reinstall from the AMD index (§3).

## 5. Train

```powershell
mkdir C:\YOLO\run1; cd C:\YOLO\run1
yolo train model=yolo26n.pt data=coco8.yaml epochs=1 device=-1
```

## 6. Use the result

- best model: `runs\detect\train\weights\best.pt`
- inference: `yolo predict model=runs\detect\train\weights\best.pt source=image.jpg device=-1`
- resume: `yolo train resume runs\detect\train\weights\last.pt`

## 7. Common problems → [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## 8. Uninstall

`pip uninstall` inside the venv, then delete `C:\YOLO\`. Nothing was installed
system-wide; no DLL was replaced.
