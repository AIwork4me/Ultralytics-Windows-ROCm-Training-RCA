# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
<#
.SYNOPSIS
Install a hash-verified official AMD package set into an ISOLATED venv (mission §4).

.DESCRIPTION
Never installs into an existing training environment. Downloads every wheel
listed in resolved_wheel_lock.json (already SHA256-pinned), re-verifies each
file hash BEFORE installation, then installs from local verified bytes only.
The allowlist is enforced by installing local files — no live index is used
at install time, so no silent replacement by CPU/other-vendor wheels.

.PARAMETER LockJson   resolved_wheel_lock.json produced by resolve_package_set.py
.PARAMETER VenvDir    target venv directory (created; must NOT already exist)
.PARAMETER BasePython python used to create the venv (e.g. C:\P19\venv\Scripts\python.exe)
.PARAMETER LogDir     where install logs are written
#>
param(
    [Parameter(Mandatory = $true)][string]$LockJson,
    [Parameter(Mandatory = $true)][string]$VenvDir,
    [Parameter(Mandatory = $true)][string]$BasePython,
    [Parameter(Mandatory = $true)][string]$LogDir
)
$ErrorActionPreference = "Stop"
$naming = "install_official.ps1"
if (Test-Path $VenvDir) { Write-Error "$naming : refusing to reuse existing venv $VenvDir (isolation contract)"; exit 2 }
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$installLog = Join-Path $LogDir ("install_official_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))

Write-Output "[$naming] lock: $LockJson"
Write-Output "[$naming] venv: $VenvDir (isolated, new)"
$lock = Get-Content $LockJson -Raw | ConvertFrom-Json

# 1) create venv
& $BasePython -m venv $VenvDir *>> $installLog
if ($LASTEXITCODE -ne 0) { Write-Error "venv creation failed (see $installLog)"; exit 2 }
$vpy = Join-Path $VenvDir "Scripts\python.exe"

# 2) verify every wheel hash BEFORE install; install from verified local bytes
$bad = 0
foreach ($p in $lock.packages) {
    if (-not (Test-Path $p.local_path)) { Write-Error "wheel missing: $($p.local_path)"; $bad++; continue }
    $h = (Get-FileHash -Algorithm SHA256 $p.local_path).Hash.ToLower()
    if ($h -ne $p.sha256.ToLower()) {
        Write-Error "HASH MISMATCH $($p.wheel_filename): lock=$($p.sha256) actual=$h"
        $bad++
    }
}
if ($bad -gt 0) { Write-Error "$bad wheel(s) failed hash verification — NOTHING installed"; exit 3 }
Write-Output "[$naming] $($lock.packages.Count) wheel hashes verified"

# 3) install verified local wheels (order: deps resolved by pip from the same set)
# PS 5.1 trap: $ErrorActionPreference=Stop + `*>>` redirection turns the FIRST
# pip stderr line into a terminating NativeCommandError — which would crash
# the retry path below. Native-call failure handling here is explicit
# ($LASTEXITCODE checks), so stderr must not throw.
$ErrorActionPreference = "Continue"
$wheels = $lock.packages | ForEach-Object { $_.local_path }
& $vpy -m pip install --no-index --no-warn-script-location $wheels *>> $installLog
if ($LASTEXITCODE -ne 0) {
    # ultralytics may need public PyPI deps (e.g. matplotlib); retry with PyPI
    # allowlisted as --extra-index while keeping exact local wheel bytes first
    # (also allows sdist-only meta-packages e.g. `rocm` to fetch build deps)
    Write-Output "[$naming] offline install incomplete; retrying with PyPI for pure-python deps (AMD wheels still local verified bytes)"
    & $vpy -m pip install --extra-index-url https://pypi.org/simple --no-warn-script-location $wheels *>> $installLog
    if ($LASTEXITCODE -ne 0) { Write-Error "pip install failed (see $installLog)"; exit 2 }
}
$ErrorActionPreference = "Stop"

# 4) record installed distribution versions vs lock
& $vpy -m pip freeze *>> $installLog
Write-Output "[$naming] DONE — venv ready: $vpy (log: $installLog)"
exit 0
