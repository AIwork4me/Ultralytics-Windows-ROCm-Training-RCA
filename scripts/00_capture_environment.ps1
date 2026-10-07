# Phase 0: capture Windows/GPU/conda/pip/torch environment baseline.
# Non-destructive: only reads system state and writes evidence logs.
#
# Usage:  powershell -ExecutionPolicy Bypass -File 00_capture_environment.ps1
#         [-Python "C:\Users\rocm\miniconda3\python.exe"] [-OutDir ..\evidence\raw\environment]
param(
    [string]$Python = "C:\Users\rocm\miniconda3\python.exe",
    [string]$OutDir = ""
)

$ErrorActionPreference = "Continue"
if (-not $OutDir) { $OutDir = Join-Path $PSScriptRoot "..\evidence\raw\environment" }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function Write-Log($Name, $ScriptBlock) {
    $path = Join-Path $OutDir $Name
    "### captured $(Get-Date -Format o)" | Out-File -FilePath $path -Encoding utf8
    try { & $ScriptBlock 2>&1 | Out-File -FilePath $path -Append -Encoding utf8 }
    catch { "CAPTURE-ERROR: $_" | Out-File -FilePath $path -Append -Encoding utf8 }
    "exit_code=$LASTEXITCODE" | Out-File -FilePath $path -Append -Encoding utf8
    Write-Host "wrote $path"
}

Write-Log "windows_os.txt" {
    Get-CimInstance Win32_OperatingSystem |
        Select-Object Caption, Version, BuildNumber, OSArchitecture |
        Format-List | Out-String
}

Write-Log "cpu.txt" {
    Get-CimInstance Win32_Processor |
        Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed |
        Format-List | Out-String
}

Write-Log "gpu_wmi.txt" {
    Get-CimInstance Win32_VideoController |
        Select-Object Name, DriverVersion, AdapterRAM, VideoProcessor |
        Format-List | Out-String
}

Write-Log "conda_env_list.txt" { & "$env:USERPROFILE\miniconda3\Scripts\conda.exe" env list }
Write-Log "conda_info.txt" { & "$env:USERPROFILE\miniconda3\Scripts\conda.exe" info }
Write-Log "conda_list_base.txt" { & "$env:USERPROFILE\miniconda3\Scripts\conda.exe" list }

Write-Log "pip_version.txt" { & $Python -m pip --version }
Write-Log "pip_freeze.txt" { & $Python -m pip freeze }
Write-Log "pip_check.txt" { & $Python -m pip check }

Write-Log "torch_collect_env.txt" { & $Python -m torch.utils.collect_env }
Write-Log "torch_probe.txt" { & $Python (Join-Path $PSScriptRoot "00_env_probe.py") }
