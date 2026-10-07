# Phase 6: AMP falsification — run the same 1-epoch GPU training with amp=False.
# If the failure persists with an identical signature, AMP is falsified as the
# primary cause. Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File 07_ultralytics_amp_falsification.ps1
param(
    [string]$Yolo = "C:\Users\rocm\miniconda3\Scripts\yolo.exe",
    [string]$WorkDir = "C:\Users\rocm\Desktop\YOLO_AMD"
)
$ErrorActionPreference = "Continue"
$OutFile = Join-Path $PSScriptRoot "..\evidence\raw\ultralytics\train_gpu_amp_off.txt"
New-Item -ItemType Directory -Force -Path (Split-Path $OutFile) | Out-Null

Push-Location $WorkDir
"### captured $(Get-Date -Format o)" | Out-File $OutFile -Encoding utf8
"### command: yolo detect train data=coco8.yaml model=yolo26n.pt epochs=1 imgsz=640 device=0 workers=0 amp=False" | Out-File $OutFile -Append -Encoding utf8

& $Yolo detect train data=coco8.yaml model=yolo26n.pt epochs=1 imgsz=640 device=0 workers=0 amp=False 2>&1 |
    ForEach-Object { "$_" } | Out-File $OutFile -Append -Encoding utf8 -Width 4096
"exit_code=$LASTEXITCODE" | Out-File $OutFile -Append -Encoding utf8
Pop-Location
Write-Host "wrote $OutFile (exit_code=$LASTEXITCODE)"
