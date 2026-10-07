# Phase 8: run the minimal BatchNorm repro in a child process with MIOpen
# logging enabled and TEMP/TMP redirected to a repo-local untracked directory,
# so generated COMGR files can be inspected before cleanup.
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File 08_miopen_logging.ps1
param(
    [string]$Python = "C:\Users\rocm\miniconda3\python.exe",
    [string]$RepoRoot = (Split-Path $PSScriptRoot -Parent)
)
$ErrorActionPreference = "Continue"
$OutDir = Join-Path $RepoRoot "evidence\raw\miopen"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$TmpDir = Join-Path $RepoRoot "evidence\tmp\miopen_run"
if (Test-Path $TmpDir) { Remove-Item -Recurse -Force $TmpDir }
New-Item -ItemType Directory -Force -Path $TmpDir | Out-Null

$env:MIOPEN_ENABLE_LOGGING = "1"
$env:MIOPEN_ENABLE_LOGGING_CMD = "1"
$env:TEMP = $TmpDir
$env:TMP = $TmpDir

$OutFile = Join-Path $OutDir "minimal_bn_miopen_logging.txt"
"### captured $(Get-Date -Format o)" | Out-File $OutFile -Encoding utf8
"### command: MIOPEN_ENABLE_LOGGING=1 MIOPEN_ENABLE_LOGGING_CMD=1 TEMP=$TmpDir python scripts/02_batchnorm_minimal.py minimal" | Out-File $OutFile -Append -Encoding utf8

& $Python (Join-Path $PSScriptRoot "02_batchnorm_minimal.py") minimal 2>&1 |
    ForEach-Object { "$_" } | Out-File $OutFile -Append -Encoding utf8 -Width 8192
"exit_code=$LASTEXITCODE" | Out-File $OutFile -Append -Encoding utf8

# Inventory what survived in the redirected temp tree.
$InvFile = Join-Path $OutDir "temp_tree_inventory.txt"
"### captured $(Get-Date -Format o)" | Out-File $InvFile -Encoding utf8
"### temp dir: $TmpDir" | Out-File $InvFile -Append -Encoding utf8
Get-ChildItem -Recurse -Force $TmpDir |
    Select-Object FullName, Length |
    Format-Table -AutoSize | Out-String -Width 4096 |
    Out-File $InvFile -Append -Encoding utf8

# Preserve surviving text sources under raw evidence (never binary outputs).
$DumpDir = Join-Path $OutDir "comgr_dump"
Get-ChildItem -Recurse -Force $TmpDir -Include *.cpp, *.hpp, *.h, *.inl, *.log, *.txt -ErrorAction SilentlyContinue |
    ForEach-Object {
        $rel = $_.FullName.Substring($TmpDir.Length + 1)
        $dest = Join-Path $DumpDir ($rel -replace '[\\/]', '__')
        New-Item -ItemType Directory -Force -Path $DumpDir | Out-Null
        Copy-Item $_.FullName $dest -Force
    }
Get-ChildItem $DumpDir -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "preserved: $($_.Name)" }
Write-Host "wrote $OutFile"
