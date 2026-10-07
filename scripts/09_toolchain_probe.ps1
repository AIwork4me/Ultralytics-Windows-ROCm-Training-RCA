# Phase 9: host C++ toolchain / <type_traits> discovery. READ-ONLY probe.
# Answers: is a host C++ standard library physically present on this machine,
# and would HIPRTC be able to discover it? Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File 09_toolchain_probe.ps1
$ErrorActionPreference = "Continue"
$OutFile = Join-Path $PSScriptRoot "..\evidence\raw\toolchain\toolchain_probe.txt"
New-Item -ItemType Directory -Force -Path (Split-Path $OutFile) | Out-Null

"### captured $(Get-Date -Format o)" | Out-File $OutFile -Encoding utf8

function Log($s) { $s | Out-File $OutFile -Append -Encoding utf8; Write-Host $s }

Log "--- where.exe probes ---"
foreach ($tool in "cl", "clang", "clang++", "hipcc", "vswhere", "dumpbin", "gcc", "g++", "link", "rc") {
    $found = & where.exe $tool 2>&1 | Select-Object -First 3
    if ($LASTEXITCODE -eq 0) { Log "$tool : $found" } else { Log "$tool : NOT FOUND" }
}

Log "--- Visual Studio vswhere discovery ---"
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (Test-Path $vswhere) {
    & $vswhere -all -products * -format json 2>&1 | Out-File $OutFile -Append -Encoding utf8
} else {
    Log "vswhere.exe not present at $vswhere"
}

Log "--- narrow search: VC\Tools\MSVC\*\include\type_traits ---"
$msvcRoots = @(
    "${env:ProgramFiles(x86)}\Microsoft Visual Studio",
    "$env:ProgramFiles\Microsoft Visual Studio"
)
$foundTraits = @()
foreach ($root in $msvcRoots) {
    if (Test-Path $root) {
        $foundTraits += Get-ChildItem -Path $root -Recurse -Filter "type_traits" -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match 'MSVC.*\\include' } |
            Select-Object -ExpandProperty FullName
    } else { Log "no dir: $root" }
}
if ($foundTraits) { $foundTraits | ForEach-Object { Log "FOUND: $_" } }
else { Log "no MSVC type_traits found under Program Files Visual Studio roots" }

Log "--- other C++ std library locations (read-only spot checks) ---"
$spots = @(
    "C:\Program Files\LLVM\include\c++",
    "C:\Strawberry\c\include\c++",
    "$env:USERPROFILE\miniconda3\Library\include\c++",
    "$env:USERPROFILE\miniconda3\include\c++",
    "C:\Program Files\Git\usr\lib\gcc",
    "C:\msys64\usr\lib\gcc",
    "C:\Program Files\Git\usr\include\c++"
)
foreach ($s in $spots) {
    if (Test-Path $s) {
        $hits = Get-ChildItem -Path $s -Recurse -Filter "type_traits" -ErrorAction SilentlyContinue |
            Select-Object -First 3 -ExpandProperty FullName
        if ($hits) { $hits | ForEach-Object { Log "FOUND: $_" } } else { Log "dir exists, no type_traits: $s" }
    } else { Log "absent: $s" }
}

Log "--- relevant env vars ---"
foreach ($v in "INCLUDE", "LIB", "LIBPATH", "CPATH", "CPLUS_INCLUDE_PATH", "HIP_PATH", "ROCM_PATH") {
    $val = [Environment]::GetEnvironmentVariable($v)
    if (-not $val) { $val = "<unset>" }
    Log "$v=$val"
}

Log "--- hiprtc/clang resources shipped in ROCm wheel (site-packages\_rocm_sdk_libraries) ---"
$rocmBin = "$env:USERPROFILE\miniconda3\Lib\site-packages\_rocm_sdk_libraries\bin"
Get-ChildItem $rocmBin -Recurse -Include "*hiprtc*", "*clang*" -ErrorAction SilentlyContinue |
    Select-Object -First 20 -ExpandProperty FullName | ForEach-Object { Log "wheel file: $_" }

# Does the wheel ship any C++ standard headers for device compilation?
$hdrRoots = @("$env:USERPROFILE\miniconda3\Lib\site-packages\_rocm_sdk_libraries")
foreach ($h in $hdrRoots) {
    $tt = Get-ChildItem -Path $h -Recurse -Filter "type_traits" -ErrorAction SilentlyContinue |
        Select-Object -First 5 -ExpandProperty FullName
    if ($tt) { $tt | ForEach-Object { Log "WHEEL FOUND: $_" } } else { Log "no type_traits anywhere under $h" }
}

Log "--- probe complete ---"
Write-Host "wrote $OutFile"
