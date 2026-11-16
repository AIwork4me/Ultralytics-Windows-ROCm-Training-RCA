# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
<#
.SYNOPSIS
Windows Radeon YOLO Golden Path harness — one entry point (mission §3, hardened R21.1 TASK A).

.DESCRIPTION
Modes (explicit; DEFAULT = -Preflight; no mode ever installs packages or
starts a long GPU workload by surprise):

  -Preflight            machine/env baseline only (no install, no GPU load)
  -EngineeringReference full R21 pipeline on the engineering-reference stack
                        (isolated venv; HIPRTC shim disclosed; classified
                        ENGINEERING_REFERENCE — never an OFFICIAL verdict)
  -OfficialCandidate    full gates on a candidate lock JSON (dev/nightly/rc
                        channel) → at most *_CANDIDATE_PASS (includes the
                        exact Ultralytics CLI train_yolo.ps1 gate G3)
  -OfficialStable       full gates on a stable-channel lock JSON → the only
                        mode that can earn OFFICIAL_STABLE_PASS (includes G3)
  -PrepareRelease       R22 channel scan + watchlist/matrix regeneration +
                        R23 doc checks; no GPU work

FAIL-CLOSED GATE ORCHESTRATION (R21.1): every gate invocation is followed by
an individual exit-code check. A mandatory gate failing (or crashing) STOPS
the sequence and records NO-GO in <evidence>\gate_status.json. The harness
NEVER returns success merely because generate_report.py exited 0 — its own
recorded gate statuses decide the final exit code.
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
    [string]$AncestryEvidence = "",       # channel binary audit JSON (source-lineage proof)
    [switch]$SkipInstall                  # reuse an existing workspace venv
)
$ErrorActionPreference = "Stop"
if (-not $HarnessRoot) { $HarnessRoot = $PSScriptRoot }
$scripts = Join-Path $HarnessRoot "scripts"
if (-not $AncestryEvidence) {
    $AncestryEvidence = Join-Path $HarnessRoot "..\evidence\raw\r22-dev\r22_channel_binary_audit.json"
}
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$evDir = Join-Path $Workspace "evidence\r21"
$logDir = Join-Path $Workspace "logs"
New-Item -ItemType Directory -Force -Path $evDir, $logDir | Out-Null

function Banner([string]$text) { Write-Host ""; Write-Host ("=" * 70); Write-Host $text; Write-Host ("=" * 70) }

# --- fail-closed gate orchestration (R21.1 TASK A) ---------------------------
# Every gate runs through Invoke-Gate: individual exit-code check, durable
# gate_status.json, immediate NO-GO stop when a mandatory gate fails.
$script:GateStatus = @()

function Save-GateStatus([string]$Overall) {
    $state = @{
        run_id     = "GP-$Mode-$stamp"
        mode       = $Mode
        updated    = (Get-Date).ToUniversalTime().ToString("o")
        overall    = $Overall
        gates      = $script:GateStatus
        contract   = "gate exit code != 0 OR gate crash => NO-GO stop; report exit 0 alone never yields success"
    }
    $dir = if ($script:GateEvDir) { $script:GateEvDir } else { $evDir }
    # UTF8 WITHOUT BOM (PS 5.1 Set-Content -Encoding UTF8 adds one, which
    # breaks strict JSON readers downstream)
    $json = $state | ConvertTo-Json -Depth 6
    [System.IO.File]::WriteAllText((Join-Path $dir "gate_status.json"), $json,
        (New-Object System.Text.UTF8Encoding($false)))
}

function Invoke-Gate {
    param(
        [Parameter(Mandatory = $true)][string]$Gate,
        [Parameter(Mandatory = $true)][scriptblock]$Body,
        [int[]]$AcceptCodes = @(0)
    )
    Write-Host ""
    Write-Host ("[" + $Gate + "] START " + ("-" * 40))
    $exit = $null
    try {
        # a gate's authority is its EXIT CODE; native stderr lines (python
        # warnings, MIOpen logs) must never become terminating PS errors —
        # PS 5.1 + `*>>` + EAP=Stop would throw on the first stderr line and
        # lose the real exit status
        $ErrorActionPreference = "Continue"
        & $Body
        $ErrorActionPreference = "Stop"
        if ($null -ne $LASTEXITCODE) { $exit = $LASTEXITCODE }
    } catch {
        $ErrorActionPreference = "Stop"
        Write-Host ("[" + $Gate + "] CRASH: " + $_.Exception.Message) -ForegroundColor Red
        $exit = -1
    }
    $ok = ($null -ne $exit) -and ($AcceptCodes -contains $exit)
    $script:GateStatus += @{
        gate = $Gate; exit_code = $exit; accepted = $ok
        status = if ($ok) { "PASS" } else { "FAIL" }
        ended_utc = (Get-Date).ToUniversalTime().ToString("o")
    }
    Save-GateStatus -Overall "RUNNING"
    if (-not $ok) {
        # mandatory gate: stop immediately, record NO-GO, propagate failure —
        # a later gate or the report generator can never mask this
        Write-Host ("[" + $Gate + "] FAIL exit=$exit — MANDATORY GATE FAILED (NO-GO)") -ForegroundColor Red
        Save-GateStatus -Overall "NO_GO"
        exit 3
    }
    Write-Host ("[" + $Gate + "] PASS (exit=$exit)")
}

function Run-GateSequence([string]$VenvPy, [string]$EvDir, [string]$Expect,
                          [string]$Chan, [string]$Tag, [int]$Runs, [string]$Sequence) {
    $script:GateEvDir = $EvDir
    $wd = Join-Path $Workspace ("scratch\gptrain-" + $Tag)
    # gate output goes to <evidence>\<stem>.log SIBLINGS so every record has
    # artifact linkage at report time (generate_report.py full requires it)
    Invoke-Gate "G0_provenance" {
        & $VenvPy -I (Join-Path $scripts "verify_provenance.py") --run-id "GP-A-$Tag" --lock $LockJson `
            --ancestry-evidence $AncestryEvidence `
            --channel $Chan --out (Join-Path $EvDir "gpA_provenance.json") *> (Join-Path $EvDir "gpA_provenance.log")
    } | Out-Null
    Invoke-Gate "G2_torch_torchvision_gpu" {
        & $VenvPy -I (Join-Path $scripts "verify_torchvision_ops.py") --run-id "GP-B-$Tag" --channel $Chan `
            --out (Join-Path $EvDir "gpB_torch_gates.json") *>> (Join-Path $EvDir "gpB_torch_gates.log")
    } | Out-Null
    Invoke-Gate "G1_miopen_nostl" {
        & $VenvPy -I (Join-Path $scripts "verify_miopen_nostl.py") --run-id "GP-C-$Tag" --channel $Chan `
            --leg official --expect $Expect --out (Join-Path $EvDir "gpC_nostl.json") *>> (Join-Path $EvDir "gpC_nostl.log")
    } | Out-Null
    # G3: the EXACT standard Ultralytics CLI command (never skipped in
    # candidate/stable sequences — R21.1 TASK A)
    Invoke-Gate "G3_ultralytics_cli" {
        & (Join-Path $scripts "train_yolo.ps1") -VenvDir (Split-Path (Split-Path $VenvPy)) `
            -WorkDir $wd -OutJson (Join-Path $EvDir "gpD_train_cli.json") -RunId "GP-D-$Tag" -Channel $Chan `
            *>> (Join-Path $EvDir "gpD_train_cli.log")
        Copy-Item (Join-Path $wd "train_stdout.log") (Join-Path $EvDir "gpD_train_stdout.log") -ErrorAction SilentlyContinue
    } | Out-Null
    Invoke-Gate "G4_optimizer_update" {
        & $VenvPy -I (Join-Path $scripts "audit_optimizer.py") --run-id "GP-E-$Tag" --channel $Chan `
            --out (Join-Path $EvDir "gpE_optimizer.json") `
            --run-dir (Join-Path $Workspace ("scratch\gpopt-" + $Tag)) *>> (Join-Path $EvDir "gpE_optimizer.log")
    } | Out-Null
    Invoke-Gate "G5_checkpoint_resume" {
        & $VenvPy -I (Join-Path $scripts "verify_checkpoint_resume.py") --run-id "GP-F-$Tag" --channel $Chan `
            --out (Join-Path $EvDir "gpF_resume.json") --work-dir (Join-Path $Workspace ("scratch\gpres-" + $Tag)) *>> (Join-Path $EvDir "gpF_resume.log")
    } | Out-Null
    Invoke-Gate "G8_reliability" {
        & $VenvPy -I (Join-Path $scripts "run_stability.py") --run-id "GP-G-$Tag" --channel $Chan `
            --runs $Runs --cold --out (Join-Path $EvDir "gpH_stability.json") `
            --work-dir (Join-Path $Workspace ("scratch\gpstab-" + $Tag)) *>> (Join-Path $EvDir "gpH_stability.log")
    } | Out-Null
    # report generation is itself a gate, but its exit 0 can NEVER alone make
    # the harness succeed — the recorded per-gate statuses decide above
    Invoke-Gate "REPORT_generate_report_full" {
        & $VenvPy -I (Join-Path $scripts "generate_report.py") full --run-id "GP-FULL-$Tag" `
            --sequence $Sequence --channel $Chan --evidence-dir $EvDir `
            --report-dir (Join-Path $HarnessRoot ("reports\gp-" + $Tag))
    } | Out-Null
    $failed = @($script:GateStatus | Where-Object { -not $_.accepted })
    Save-GateStatus -Overall $(if ($failed.Count -eq 0) { "GO" } else { "NO_GO" })
    if ($failed.Count -gt 0) { exit 3 }
    return 0
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
            Invoke-Gate "INSTALL_official_lock" {
                & (Join-Path $scripts "install_official.ps1") `
                    -LockJson (Join-Path $HarnessRoot "requirements-lock\r21-engref-lock.json") `
                    -VenvDir "$Workspace\venvs\r21-engref" -BasePython $BasePython -LogDir $logDir
            } | Out-Null
        }
        $script:GateEvDir = $evDir
        # Phase A: provenance + torch/torchvision gates
        Invoke-Gate "G0_provenance_engref" {
            & $vpy -I (Join-Path $scripts "verify_provenance.py") --run-id "R21-A-$stamp" --channel "multi-arch" `
                --out (Join-Path $evDir "r21A_provenance.json")
        } | Out-Null
        Invoke-Gate "G2_torch_torchvision_gpu" {
            & $vpy -I (Join-Path $scripts "verify_torchvision_ops.py") --run-id "R21-A2-$stamp" --channel "multi-arch" `
                --out (Join-Path $evDir "r21A2_torch_gates.json") *>> (Join-Path $logDir "r21A2.log")
        } | Out-Null
        # Phase D: no-STL legs (official leg expects pre-fix FAIL on this stack)
        Invoke-Gate "G1_miopen_nostl_official_pre_fix" {
            & $vpy -I (Join-Path $scripts "verify_miopen_nostl.py") --run-id "R21-D1-$stamp" --channel "multi-arch" `
                --leg official --expect FAIL --out (Join-Path $evDir "r21D1_nostl_official.json")
        } | Out-Null
        Invoke-Gate "G1_miopen_nostl_engineering_leg" {
            & $vpy -I (Join-Path $scripts "verify_miopen_nostl.py") --run-id "R21-D2-$stamp" --channel "multi-arch" `
                --leg engineering --out (Join-Path $evDir "r21D2_nostl_engref.json")
        } | Out-Null
        # Phase E: standard CLI train + optimizer audit + resume lifecycle
        $wd = "$Workspace\scratch\train-$stamp"; New-Item -ItemType Directory -Force -Path $wd | Out-Null
        Invoke-Gate "G3_ultralytics_cli" {
            & (Join-Path $scripts "train_yolo.ps1") -VenvDir "$Workspace\venvs\r21-engref" `
                -WorkDir $wd -OutJson (Join-Path $evDir "r21E1_train_cli.json") -RunId "R21-E1-$stamp" -Channel "multi-arch"
        } | Out-Null
        Invoke-Gate "G4_optimizer_update" {
            & $vpy -I (Join-Path $scripts "audit_optimizer.py") --run-id "R21-E2-$stamp" --channel "multi-arch" `
                --out (Join-Path $evDir "r21E2_optimizer.json") `
                --run-dir "$Workspace\scratch\optaudit-$stamp" *>> (Join-Path $logDir "r21E2.log")
        } | Out-Null
        Invoke-Gate "G5_checkpoint_resume" {
            & $vpy -I (Join-Path $scripts "verify_checkpoint_resume.py") --run-id "R21-E3-$stamp" --channel "multi-arch" `
                --out (Join-Path $evDir "r21E3_resume.json") --work-dir "$Workspace\scratch\resume-$stamp" *>> (Join-Path $logDir "r21E3.log")
        } | Out-Null
        Invoke-Gate "G8_reliability" {
            & $vpy -I (Join-Path $scripts "run_stability.py") --run-id "R21-F-$stamp" --channel "multi-arch" `
                --runs $StabilityRuns --out (Join-Path $evDir "r21F_stability.json") `
                --work-dir "$Workspace\scratch\stability-$stamp" *>> (Join-Path $logDir "r21F.log")
        } | Out-Null
        Invoke-Gate "REPORT_generate_report_full" {
            & $vpy -I (Join-Path $scripts "generate_report.py") full --run-id "R21-FULL-$stamp" `
                --sequence engref --channel "multi-arch" --evidence-dir $evDir `
                --report-dir (Join-Path $HarnessRoot "reports\r21-$stamp")
        } | Out-Null
        $failed = @($script:GateStatus | Where-Object { -not $_.accepted })
        Save-GateStatus -Overall $(if ($failed.Count -eq 0) { "GO" } else { "NO_GO" })
        if ($failed.Count -gt 0) { exit 3 }
        exit 0
    }
    "OfficialCandidate" {
        if (-not $LockJson) { Write-Error "-OfficialCandidate requires -LockJson"; exit 2 }
        Banner "MODE: OfficialCandidate — candidate-channel gates; max verdict RC/NIGHTLY/DEV_CANDIDATE_PASS (never OFFICIAL_STABLE_PASS)"
        $chan = (Get-Content $LockJson -Raw | ConvertFrom-Json).channel
        if ($chan -eq "stable") { Write-Error "lock channel is 'stable': use -OfficialStable for stable acceptance"; exit 2 }
        $vpy = "$Workspace\venvs\r22-candidate\Scripts\python.exe"
        if (-not (Test-Path $vpy)) {
            Invoke-Gate "INSTALL_official_lock" {
                & (Join-Path $scripts "install_official.ps1") -LockJson $LockJson `
                    -VenvDir "$Workspace\venvs\r22-candidate" -BasePython $BasePython -LogDir $logDir
            } | Out-Null
        }
        $ev2 = Join-Path $Workspace "evidence\r22-candidate"; New-Item -ItemType Directory -Force -Path $ev2 | Out-Null
        $code = Run-GateSequence -VenvPy $vpy -EvDir $ev2 -Expect "CANDIDATE" -Chan $chan -Tag $stamp -Runs 10 -Sequence "candidate"
        exit $code
    }
    "OfficialStable" {
        if (-not $LockJson) { Write-Error "-OfficialStable requires -LockJson"; exit 2 }
        $chan = (Get-Content $LockJson -Raw | ConvertFrom-Json).channel
        if ($chan -ne "stable") { Write-Error "-OfficialStable refused: lock channel is '$chan' (stable only)"; exit 2 }
        Banner "MODE: OfficialStable — stable-channel acceptance (G0..G9); OFFICIAL_STABLE_PASS requires every gate incl. both gfx + clean Windows"
        $vpy = "$Workspace\venvs\r22-stable\Scripts\python.exe"
        if (-not (Test-Path $vpy)) {
            Invoke-Gate "INSTALL_official_lock" {
                & (Join-Path $scripts "install_official.ps1") -LockJson $LockJson `
                    -VenvDir "$Workspace\venvs\r22-stable" -BasePython $BasePython -LogDir $logDir
            } | Out-Null
        }
        $ev3 = Join-Path $Workspace "evidence\r22-stable"; New-Item -ItemType Directory -Force -Path $ev3 | Out-Null
        $code = Run-GateSequence -VenvPy $vpy -EvDir $ev3 -Expect "STABLE" -Chan "stable" -Tag $stamp -Runs 10 -Sequence "stable"
        exit $code
    }
    "PrepareRelease" {
        Banner "MODE: PrepareRelease — R22 channel scan + artifacts regeneration (no GPU)"
        & $BasePython -I (Join-Path $scripts "discover_official_wheels.py") `
            --out-dir (Join-Path $evDir "wheel-scan") --gfx $Gfx
        exit $LASTEXITCODE
    }
}
