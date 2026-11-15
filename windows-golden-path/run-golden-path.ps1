# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
<#
.SYNOPSIS
Windows Radeon YOLO Golden Path harness — one entry point (mission §3).

.DESCRIPTION
Modes (explicit; DEFAULT = -Preflight; no mode ever installs packages or
starts a long GPU workload by surprise):

  -Preflight            machine/env baseline only (no install, no GPU load)
  -EngineeringReference full R21 pipeline on the engineering-reference stack
                        (isolated venv; HIPRTC shim disclosed; classified
                        ENGINEERING_REFERENCE — never an OFFICIAL verdict)
  -OfficialCandidate    full gates on a candidate lock JSON (dev/nightly/rc
                        channel) → at most *_CANDIDATE_PASS
  -OfficialStable       full gates on a stable-channel lock JSON → the only
                        mode that can earn OFFICIAL_STABLE_PASS
  -PrepareRelease       R22 channel scan + watchlist/matrix regeneration +
                        R23 doc checks; no GPU work

Every mode prints its runtime classification clearly before doing anything.
#>
param(
    [Parameter(Mandatory = $true)][ValidateSet("Preflight", "EngineeringReference",
        "OfficialCandidate", "OfficialStable", "PrepareRelease")][string]$Mode = "Preflight",
    [string]$LockJson = "",
    [string]$Workspace = "C:\RadeonYOLO",
    [string]$HarnessRoot = "",            # default: this script's directory
    [string]$BasePython = "C:\P19\venv\Scripts\python.exe",
    [string]$Gfx = "gfx1100",
    [int]$StabilityRuns = 3,              # R21 default; R22 acceptance uses 10
    [switch]$SkipInstall                  # reuse an existing workspace venv
)
$ErrorActionPreference = "Stop"
if (-not $HarnessRoot) { $HarnessRoot = $PSScriptRoot }
$scripts = Join-Path $HarnessRoot "scripts"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$evDir = Join-Path $Workspace "evidence\r21"
$logDir = Join-Path $Workspace "logs"
New-Item -ItemType Directory -Force -Path $evDir, $logDir | Out-Null

function Banner([string]$text) { Write-Host ""; Write-Host ("=" * 70); Write-Host $text; Write-Host ("=" * 70) }

    function Run-GateSequence([string]$VenvPy, [string]$EvDir, [string]$Expect,
                               [string]$Chan, [string]$Tag, [int]$Runs) {
        & $VenvPy -I (Join-Path $scripts "verify_provenance.py") --run-id "GP-A-$Tag" --lock $LockJson `
            --channel $Chan --out (Join-Path $EvDir "gpA_provenance.json")
        & $VenvPy -I (Join-Path $scripts "verify_torchvision_ops.py") --run-id "GP-B-$Tag" `
            --out (Join-Path $EvDir "gpB_torch_gates.json") *>> (Join-Path $logDir "gpB-$Tag.log")
        & $VenvPy -I (Join-Path $scripts "verify_miopen_nostl.py") --run-id "GP-C-$Tag" `
            --leg official --expect $Expect --out (Join-Path $EvDir "gpC_nostl.json") *>> (Join-Path $logDir "gpC-$Tag.log")
        & $VenvPy -I (Join-Path $scripts "audit_optimizer.py") --run-id "GP-D-$Tag" `
            --out (Join-Path $EvDir "gpD_optimizer.json") `
            --run-dir "$Workspace\scratch\gpopt-$Tag" *>> (Join-Path $logDir "gpD-$Tag.log")
        & $VenvPy -I (Join-Path $scripts "verify_checkpoint_resume.py") --run-id "GP-E-$Tag" `
            --out (Join-Path $EvDir "gpE_resume.json") --work-dir "$Workspace\scratch\gpres-$Tag" *>> (Join-Path $logDir "gpE-$Tag.log")
        & $VenvPy -I (Join-Path $scripts "run_stability.py") --run-id "GP-F-$Tag" `
            --runs $Runs --cold --out (Join-Path $EvDir "gpF_stability.json") `
            --work-dir "$Workspace\scratch\gpstab-$Tag" *>> (Join-Path $logDir "gpF-$Tag.log")
        & $VenvPy -I (Join-Path $scripts "generate_report.py") full --run-id "GP-FULL-$Tag" `
            --evidence-dir $EvDir --report-dir (Join-Path $HarnessRoot "reports\gp-$Tag")
        return $LASTEXITCODE
    }

switch ($Mode) {
    "Preflight" {
        Banner "MODE: Preflight — environment baseline only (no install, no GPU workload)"
        & $BasePython -I (Join-Path $scripts "check_environment.py") `
            --out (Join-Path $evDir "R21_ENVIRONMENT_BASELINE.json") `
            --venv-python $(if (Test-Path "$Workspace\venvs\r21-engref\Scripts\python.exe") { "$Workspace\venvs\r21-engref\Scripts\python.exe" } else { $BasePython })
        exit $LASTEXITCODE
    }
    "EngineeringReference" {
        Banner "MODE: EngineeringReference — CLASSIFICATION WILL BE ENGINEERING_REFERENCE (HIPRTC shim disclosed; wheel bytes official)"
        $vpy = "$Workspace\venvs\r21-engref\Scripts\python.exe"
        if (-not (Test-Path $vpy)) {
            if ($SkipInstall) { Write-Error "venv missing and -SkipInstall given"; exit 2 }
            & (Join-Path $scripts "install_official.ps1") `
                -LockJson (Join-Path $HarnessRoot "requirements-lock\r21-engref-lock.json") `
                -VenvDir "$Workspace\venvs\r21-engref" -BasePython $BasePython -LogDir $logDir
            if ($LASTEXITCODE -ne 0) { exit 2 }
        }
        # Phase A: provenance + torch/torchvision gates
        & $vpy -I (Join-Path $scripts "verify_provenance.py") --run-id "R21-A-$stamp" `
            --out (Join-Path $evDir "r21A_provenance.json")
        & $vpy -I (Join-Path $scripts "verify_torchvision_ops.py") --run-id "R21-A2-$stamp" `
            --out (Join-Path $evDir "r21A2_torch_gates.json") *>> (Join-Path $logDir "r21A2.log")
        # Phase D: no-STL legs (official leg expects pre-fix FAIL on this stack)
        & $vpy -I (Join-Path $scripts "verify_miopen_nostl.py") --run-id "R21-D1-$stamp" `
            --leg official --expect FAIL --out (Join-Path $evDir "r21D1_nostl_official.json")
        & $vpy -I (Join-Path $scripts "verify_miopen_nostl.py") --run-id "R21-D2-$stamp" `
            --leg engineering --out (Join-Path $evDir "r21D2_nostl_engref.json")
        # Phase E: standard CLI train + optimizer audit + resume lifecycle
        $wd = "$Workspace\scratch\train-$stamp"; New-Item -ItemType Directory -Force -Path $wd | Out-Null
        & (Join-Path $scripts "train_yolo.ps1") -VenvDir "$Workspace\venvs\r21-engref" `
            -WorkDir $wd -OutJson (Join-Path $evDir "r21E1_train_cli.json") -RunId "R21-E1-$stamp"
        & $vpy -I (Join-Path $scripts "audit_optimizer.py") --run-id "R21-E2-$stamp" `
            --out (Join-Path $evDir "r21E2_optimizer.json") `
            --run-dir "$Workspace\scratch\optaudit-$stamp" *>> (Join-Path $logDir "r21E2.log")
        & $vpy -I (Join-Path $scripts "verify_checkpoint_resume.py") --run-id "R21-E3-$stamp" `
            --out (Join-Path $evDir "r21E3_resume.json") --work-dir "$Workspace\scratch\resume-$stamp" *>> (Join-Path $logDir "r21E3.log")
        & $vpy -I (Join-Path $scripts "run_stability.py") --run-id "R21-F-$stamp" `
            --runs $StabilityRuns --out (Join-Path $evDir "r21F_stability.json") `
            --work-dir "$Workspace\scratch\stability-$stamp" *>> (Join-Path $logDir "r21F.log")
        & $vpy -I (Join-Path $scripts "generate_report.py") full --run-id "R21-FULL-$stamp" `
            --evidence-dir $evDir --report-dir (Join-Path $HarnessRoot "reports\r21-$stamp")
        exit $LASTEXITCODE
    }
    "OfficialCandidate" {
        if (-not $LockJson) { Write-Error "-OfficialCandidate requires -LockJson"; exit 2 }
        Banner "MODE: OfficialCandidate — candidate-channel gates; max verdict RC/NIGHTLY/DEV_CANDIDATE_PASS (never OFFICIAL_STABLE_PASS)"
        $chan = (Get-Content $LockJson -Raw | ConvertFrom-Json).channel
        if ($chan -eq "stable") { Write-Warning "lock channel is 'stable': use -OfficialStable for stable acceptance" }
        $vpy = "$Workspace\venvs\r22-candidate\Scripts\python.exe"
        if (-not (Test-Path $vpy)) {
            & (Join-Path $scripts "install_official.ps1") -LockJson $LockJson `
                -VenvDir "$Workspace\venvs\r22-candidate" -BasePython $BasePython -LogDir $logDir
            if ($LASTEXITCODE -ne 0) { exit 2 }
        }
        $ev2 = Join-Path $Workspace "evidence\r22-candidate"; New-Item -ItemType Directory -Force -Path $ev2 | Out-Null
        $code = Run-GateSequence -VenvPy $vpy -EvDir $ev2 -Expect "CANDIDATE" -Chan $chan -Tag $stamp -Runs 10
        exit $code
    }
    "OfficialStable" {
        if (-not $LockJson) { Write-Error "-OfficialStable requires -LockJson"; exit 2 }
        $chan = (Get-Content $LockJson -Raw | ConvertFrom-Json).channel
        if ($chan -ne "stable") { Write-Error "-OfficialStable refused: lock channel is '$chan' (stable only)"; exit 2 }
        Banner "MODE: OfficialStable — stable-channel acceptance (G0..G9); OFFICIAL_STABLE_PASS requires every gate incl. both gfx + clean Windows"
        $vpy = "$Workspace\venvs\r22-stable\Scripts\python.exe"
        if (-not (Test-Path $vpy)) {
            & (Join-Path $scripts "install_official.ps1") -LockJson $LockJson `
                -VenvDir "$Workspace\venvs\r22-stable" -BasePython $BasePython -LogDir $logDir
            if ($LASTEXITCODE -ne 0) { exit 2 }
        }
        $ev3 = Join-Path $Workspace "evidence\r22-stable"; New-Item -ItemType Directory -Force -Path $ev3 | Out-Null
        $code = Run-GateSequence -VenvPy $vpy -EvDir $ev3 -Expect "STABLE" -Chan "stable" -Tag $stamp -Runs 10
        exit $code
    }
    "PrepareRelease" {
        Banner "MODE: PrepareRelease — R22 channel scan + artifacts regeneration (no GPU)"
        & $BasePython -I (Join-Path $scripts "discover_official_wheels.py") `
            --out-dir (Join-Path $evDir "wheel-scan") --gfx $Gfx
        exit $LASTEXITCODE
    }
}
