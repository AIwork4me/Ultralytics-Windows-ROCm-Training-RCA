# Gate 23: clean-env reproduction runner with full provenance headers.
# Regenerates the A-F artifact set under evidence/phase2/raw/clean_env/
# with capture timestamp, exact command, interpreter, PYTHONNOUSERSITE,
# and exit code embedded in each log (per Gate-23 audit amendment 1).
#
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File 21_clean_repro.ps1
param(
    [string]$EnvPython = "C:\Users\rocm\miniconda3\envs\yolo_amd\python.exe",
    [string]$RcaRoot = "",
    [string]$WorkDir = "C:\Users\rocm\Desktop\YOLO_AMD"
)
if (-not $RcaRoot) { $RcaRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path }
$ErrorActionPreference = "Continue"
$OutDir = Join-Path $RcaRoot "evidence\phase2\raw\clean_env"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$env:PYTHONNOUSERSITE = "1"

function Invoke-Logged([string]$Tag, [string]$Desc, [scriptblock]$Block) {
    $out = Join-Path $OutDir "$Tag.txt"
    $cmd_desc = $Desc -replace "`r?`n", " "
    "### captured $(Get-Date -Format o)" | Out-File $out -Encoding utf8
    "### desc: $cmd_desc" | Out-File $out -Append -Encoding utf8
    "### interpreter: $EnvPython  PYTHONNOUSERSITE=$env:PYTHONNOUSERSITE" | Out-File $out -Append -Encoding utf8
    "### shell: plain (no VS/MSVC environment injection)" | Out-File $out -Append -Encoding utf8
    & $Block 2>&1 | ForEach-Object { "$_" } | Out-File $out -Append -Encoding utf8 -Width 4096
    "exit_code=$LASTEXITCODE" | Out-File $out -Append -Encoding utf8
    Write-Host "$Tag -> exit $LASTEXITCODE"
}

$scripts = Join-Path $RcaRoot "scripts"

Invoke-Logged "A_gemm" "Control A: GPU GEMM 4096^2 (scripts/01_gpu_gemm_control.py)" {
    & $EnvPython (Join-Path $scripts "01_gpu_gemm_control.py")
}
Invoke-Logged "B_conv" "Control B: GPU Conv2d (scripts/04_conv_control.py; NOTE warm-cache pass expected)" {
    & $EnvPython (Join-Path $scripts "04_conv_control.py")
}
Invoke-Logged "C_bn_minimal_train" "Test C: minimal BatchNorm2d(16) (8,16,64,64) train (scripts/02_batchnorm_minimal.py minimal)" {
    & $EnvPython (Join-Path $scripts "02_batchnorm_minimal.py") minimal
}
Invoke-Logged "C_bn_issue3956" "Test C-3956: BatchNorm2d(100) (20,100,35,45)" {
    & $EnvPython (Join-Path $scripts "02_batchnorm_minimal.py") issue3956
}
Invoke-Logged "C_bn_yololike" "Test C-yolo: BatchNorm2d(16) (16,16,320,320)" {
    & $EnvPython (Join-Path $scripts "02_batchnorm_minimal.py") yololike
}
Invoke-Logged "D_bn_eval" "Test D: BatchNorm2d eval (matrix case C)" {
    & $EnvPython (Join-Path $scripts "03_batchnorm_matrix.py") C
}
Invoke-Logged "E_bn_cudnn_off" "Test E: BN with torch.backends.cudnn.enabled=False (diagnostic)" {
    & $EnvPython (Join-Path $scripts "03_batchnorm_matrix.py") E
}

# Test F: YOLO GPU train (Python-API equivalent of the yolo CLI train call)
$yoloPs1 = {
    Push-Location $WorkDir
    & $EnvPython -c "from ultralytics import YOLO; YOLO('yolo26n.pt').train(data='coco8.yaml', epochs=1, imgsz=640, device=0, workers=0)"
    Pop-Location
}
$out = Join-Path $OutDir "F_yolo_train.txt"
"### captured $(Get-Date -Format o)" | Out-File $out -Encoding utf8
"### desc: Test F: Ultralytics YOLO26n GPU train coco8 epochs=1 imgsz=640 device=0 workers=0 (Python-API equivalent)" | Out-File $out -Append -Encoding utf8
"### interpreter: $EnvPython  PYTHONNOUSERSITE=$env:PYTHONNOUSERSITE" | Out-File $out -Append -Encoding utf8
"### workdir: $WorkDir" | Out-File $out -Append -Encoding utf8
& $yoloPs1 2>&1 | ForEach-Object { "$_" } | Out-File $out -Append -Encoding utf8 -Width 4096
"exit_code=$LASTEXITCODE" | Out-File $out -Append -Encoding utf8
Write-Host "F_yolo_train -> exit $LASTEXITCODE"
