# Phase 3: reproduce the original Ultralytics GPU training failure with the
# shortest command that keeps the failing path unchanged (epochs=1, workers=0).
# The original user command was:
#   yolo detect train data=coco8.yaml model=yolo26n.pt epochs=100 imgsz=640
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File 06_ultralytics_train_repro.ps1 [-Tag "gpu"]
param(
    [string]$Yolo = "C:\Users\rocm\miniconda3\Scripts\yolo.exe",
    [string]$WorkDir = "C:\Users\rocm\Desktop\YOLO_AMD",
    [string]$Tag = "gpu",
    [string]$ExtraArgs = ""
)
$ErrorActionPreference = "Continue"
$OutFile = Join-Path $PSScriptRoot "..\evidence\raw\ultralytics\train_$Tag.txt"
New-Item -ItemType Directory -Force -Path (Split-Path $OutFile) | Out-Null

Push-Location $WorkDir
"### captured $(Get-Date -Format o)" | Out-File $OutFile -Encoding utf8
"### command: yolo detect train data=coco8.yaml model=yolo26n.pt epochs=1 imgsz=640 device=0 workers=0 $ExtraArgs" | Out-File $OutFile -Append -Encoding utf8

& $Yolo detect train data=coco8.yaml model=yolo26n.pt epochs=1 imgsz=640 device=0 workers=0 $ExtraArgs 2>&1 |
    ForEach-Object { "$_" } | Out-File $OutFile -Append -Encoding utf8 -Width 4096
"exit_code=$LASTEXITCODE" | Out-File $OutFile -Append -Encoding utf8
Pop-Location
Write-Host "wrote $OutFile (exit_code=$LASTEXITCODE)"
