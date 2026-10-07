# Phase 2: Ultralytics inference control — proves model load + ROCm conv
# inference path works. Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File 05_ultralytics_inference_control.ps1
param(
    [string]$Yolo = "C:\Users\rocm\miniconda3\Scripts\yolo.exe",
    [string]$WorkDir = "C:\Users\rocm\Desktop\YOLO_AMD",
    [string]$OutFile = ""
)
$ErrorActionPreference = "Continue"
if (-not $OutFile) { $OutFile = Join-Path $PSScriptRoot "..\evidence\raw\ultralytics\predict.txt" }
New-Item -ItemType Directory -Force -Path (Split-Path $OutFile) | Out-Null

Push-Location $WorkDir
"### captured $(Get-Date -Format o)" | Out-File $OutFile -Encoding utf8
"### command: yolo predict model=yolo26n.pt source=https://ultralytics.com/images/bus.jpg device=0" | Out-File $OutFile -Append -Encoding utf8

& $Yolo predict model=yolo26n.pt source="https://ultralytics.com/images/bus.jpg" device=0 2>&1 |
    Out-File $OutFile -Append -Encoding utf8
"exit_code=$LASTEXITCODE" | Out-File $OutFile -Append -Encoding utf8
Pop-Location
Write-Host "wrote $OutFile (exit_code=$LASTEXITCODE)"
