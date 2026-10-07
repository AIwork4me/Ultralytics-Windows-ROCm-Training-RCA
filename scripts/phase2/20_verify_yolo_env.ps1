# Gate 21/22 reproduction: verify what the (yolo_amd) environment actually is.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File 20_verify_yolo_env.ps1 [-EnvPython <path>]
param(
    [string]$EnvPython = "C:\Users\rocm\miniconda3\envs\yolo_amd\python.exe"
)
$RcaRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
"=== conda env list ==="; conda env list
"=== activated-shell probe (what does (yolo_amd) execute?) ==="
cmd /c "`"$RcaRoot\scripts\phase2\gate21_probe.bat`""
"=== clean-env package probe ==="
$env:PYTHONNOUSERSITE = "1"
& $EnvPython (Join-Path $RcaRoot "scripts\phase2\gate21_env_probe.py")
