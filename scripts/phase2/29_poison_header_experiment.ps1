# Gate 27/32 reproduction: proves wheel MIOpen passes -I$ROCM_PATH/include to
# HIPRTC and that -I SHADOWS MSVC auto-discovery.
# WARNING: forces a REAL failed compile (exit 1 expected with the poison marker).
param(
    [string]$EnvPython = "C:\Users\rocm\miniconda3\envs\yolo_amd\python.exe",
    [string]$PoisonRoot = "C:\hiprtc_poison"
)
$RcaRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
New-Item -ItemType Directory -Force -Path (Join-Path $PoisonRoot "include") | Out-Null
Set-Content -Path (Join-Path $PoisonRoot "include\type_traits") -Value "#error POISONED_TYPE_TRAITS_SHIM_EXPERIMENT"
$Iso = Join-Path $env:TEMP ("poison_iso_" + [guid]::NewGuid().ToString("N").Substring(0,8))
New-Item -ItemType Directory -Force -Path (Join-Path $Iso "AppData\Local") | Out-Null
$env:PYTHONNOUSERSITE="1"; $env:ROCM_PATH=$PoisonRoot
$env:USERPROFILE=$Iso; $env:HOME=$Iso; $env:LOCALAPPDATA=Join-Path $Iso "AppData\Local"
& $EnvPython -c "import torch,torch.nn as nn; bn=nn.BatchNorm2d(4).cuda().train(); x=torch.randn(2,4,8,8,device='cuda'); y=bn(x)"
Write-Host "exit=$LASTEXITCODE (1 expected; log must contain POISONED_TYPE_TRAITS_SHIM_EXPERIMENT)"
Write-Host "isolation dir: $Iso"
