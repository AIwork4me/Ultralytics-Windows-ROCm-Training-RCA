# Gate 32: Candidate A experiment runner — MSVC-free STL shim via ROCM_PATH.
# Cache-isolated (HOME/USERPROFILE/LOCALAPPDATA redirected) so every run
# forces fresh HIPRTC compiles. The -I shim dir SHADOWS MSVC auto-discovery
# (proven by the poisoned-header test), so this isolates the shim even with
# MSVC installed.
param(
    [string]$EnvPython = "C:\Users\rocm\miniconda3\envs\yolo_amd\python.exe",
    [string]$RcaRoot = "",
    [string]$ShimRoot = "C:\Users\rocm\Desktop\YOLO_AMD\Ultralytics-Windows-ROCm-Training-RCA\patches\shim_stl",
    [string]$WorkDir = "C:\Users\rocm\Desktop\YOLO_AMD"
)
if (-not $RcaRoot) { $RcaRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path }
$OutDir = Join-Path $RcaRoot "evidence\phase2\raw\candidateA"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$IsoDir = Join-Path $env:TEMP ("gateA_iso_" + [guid]::NewGuid().ToString("N").Substring(0,8))
New-Item -ItemType Directory -Force -Path (Join-Path $IsoDir "AppData\Local") | Out-Null

$env:PYTHONNOUSERSITE = "1"
$env:ROCM_PATH = $ShimRoot
$env:USERPROFILE = $IsoDir
$env:HOME = $IsoDir
$env:LOCALAPPDATA = Join-Path $IsoDir "AppData\Local"

function Invoke-Logged([string]$Tag, [string]$Desc, [string[]]$PyArgs) {
    $out = Join-Path $OutDir "$Tag.txt"
    "### captured $(Get-Date -Format o)" | Out-File $out -Encoding utf8
    "### desc: $Desc" | Out-File $out -Append -Encoding utf8
    "### interpreter: $EnvPython  PYTHONNOUSERSITE=1  ROCM_PATH=$env:ROCM_PATH (shim)" | Out-File $out -Append -Encoding utf8
    "### cache isolation: HOME=USERPROFILE=$IsoDir" | Out-File $out -Append -Encoding utf8
    Push-Location $WorkDir
    & $EnvPython @PyArgs 2>&1 | ForEach-Object { "$_" } | Out-File $out -Append -Encoding utf8 -Width 4096
    "exit_code=$LASTEXITCODE" | Out-File $out -Append -Encoding utf8
    Pop-Location
    Write-Host "$Tag -> exit $LASTEXITCODE"
}

$s = Join-Path $RcaRoot "scripts"
Invoke-Logged "A_minimal" "Candidate A: minimal BN train with shim STL (no MSVC dependency)" @((Join-Path $s "02_batchnorm_minimal.py"), "minimal")
Invoke-Logged "A_issue3956" "Candidate A: BN issue3956 shape" @((Join-Path $s "02_batchnorm_minimal.py"), "issue3956")
Invoke-Logged "A_yololike" "Candidate A: BN yololike shape" @((Join-Path $s "02_batchnorm_minimal.py"), "yololike")
Invoke-Logged "A_eval" "Candidate A: BN eval (matrix case C)" @((Join-Path $s "03_batchnorm_matrix.py"), "C")
Invoke-Logged "A_conv" "Candidate A: Conv2d control (regression)" @((Join-Path $s "04_conv_control.py"))
Invoke-Logged "A_gemm" "Candidate A: GEMM control (regression)" @((Join-Path $s "01_gpu_gemm_control.py"))
Invoke-Logged "A_variants" "Candidate A: BN variants V1-V5" @((Join-Path $s "11_bn_variants.py"))
Write-Host "isolation dir: $IsoDir"
