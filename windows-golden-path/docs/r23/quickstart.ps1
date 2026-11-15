# Quickstart PowerShell script (R23 DRAFT — not release-qualified)
# Commands below were physically verified on RX 7900 XTX / Win11 26300 with
# the official multi-arch index on 2026-11-15 (R21 evidence).
# BLOCKER (disclosed): official STABLE MIOpen.dll is pre-#13437; training on
# machines WITHOUT Visual Studio Build Tools will hit HIPRTC 'type_traits'
# not found. Do not publish until R22 OFFICIAL_STABLE_PASS.

param(
    [string]$Root = "C:\YOLO",
    [ValidateSet("gfx1100", "gfx1151")][string]$Gfx = "gfx1100",
    [string]$Python = "python"
)
$ErrorActionPreference = "Stop"

Write-Host "== Radeon YOLO quickstart ($Gfx) — DRAFT, blocker disclosed =="

# 1) clean venv
& $Python -m venv "$Root\venv"
& "$Root\venv\Scripts\python.exe" -m pip install --quiet --upgrade pip

# 2) official AMD torch stack (verified pins)
& "$Root\venv\Scripts\python.exe" -m pip install `
    torch==2.12.0+rocm7.14.1 torchvision==0.27.0+rocm7.14.1 `
    --index-url https://repo.amd.com/rocm/whl-multi-arch/
if ($Gfx -eq "gfx1100") {
    & "$Root\venv\Scripts\python.exe" -m pip install `
        amd-torch-device-gfx1100==2.12.0+rocm7.14.1 `
        amd-torch-device-gfx110x==2.12.0+rocm7.14.1 `
        amd-torchvision-device-gfx1100==0.27.0+rocm7.14.1 `
        --index-url https://repo.amd.com/rocm/whl-multi-arch/
} else {
    & "$Root\venv\Scripts\python.exe" -m pip install `
        amd-torch-device-gfx1151==2.12.0+rocm7.14.1 `
        amd-torchvision-device-gfx1151==0.27.0+rocm7.14.1 `
        --index-url https://repo.amd.com/rocm/whl-multi-arch/
}

# 3) released Ultralytics
& "$Root\venv\Scripts\python.exe" -m pip install ultralytics==8.4.214

# 4) verify GPU
& "$Root\venv\Scripts\python.exe" -c "import torch; assert torch.cuda.is_available(); print('GPU OK:', torch.cuda.get_device_name(0))"

# 5) standard first training (COCO8 smoke)
New-Item -ItemType Directory -Force -Path "$Root\run1" | Out-Null
Push-Location "$Root\run1"
& "$Root\venv\Scripts\yolo.exe" train model=yolo26n.pt data=coco8.yaml epochs=1 device=-1
$code = $LASTEXITCODE
Pop-Location
Write-Host "train exit code: $code  (best.pt/last.pt under $Root\run1\runs\detect\train\weights)"
exit $code
