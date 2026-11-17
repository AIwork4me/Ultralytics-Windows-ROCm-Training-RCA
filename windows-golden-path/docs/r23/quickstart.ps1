# Quickstart PowerShell script (R23 DRAFT — FAIL-CLOSED, R21.1 TASK E)
#
# The DEFAULT path refuses to install anything: every official channel that
# carries a Windows MIOpen wheel today still ships the PRE-#13437 MIOpen.dll
# (stable 10.1.0 byte-identical pre-fix, rc 10.2.0rc2 branch-cut pre-fix,
# multi-arch 7.14.1 pre-fix). A default quickstart that installs a known
# pre-fix release and then runs a training would reproduce issue #3956 on
# every machine without Visual Studio Build Tools — so it must not do that.
#
#   -Mode Status                     (DEFAULT) print the current gate status
#                                    and exit 3 — nothing installed, nothing run
#   -Mode EngineeringDemonstration  EXPLICITLY-LABELED engineering mode: installs
#                                    the engineering-reference stack and runs the
#                                    demo train. The engref MIOpen.dll is pre-fix:
#                                    the documented HIPRTC 'type_traits' failure
#                                    is expected on machines WITHOUT VS Build
#                                    Tools. This is a demonstration, NOT a
#                                    release-qualified install.
#   -Mode OfficialStable            always refused here until R22 issues
#                                    OFFICIAL_STABLE_PASS (exit 4)
param(
    [string]$Root = "C:\YOLO",
    [ValidateSet("gfx1100", "gfx1151")][string]$Gfx = "gfx1100",
    [string]$Python = "python",
    [ValidateSet("Status", "EngineeringDemonstration", "OfficialStable")][string]$Mode = "Status"
)
$ErrorActionPreference = "Stop"

Write-Host "== Radeon YOLO quickstart ($Gfx) — R23 DRAFT, fail-closed =="
Write-Host "== Mode: $Mode =="

if ($Mode -eq "OfficialStable") {
    Write-Host "REFUSED: OFFICIAL_STABLE_PASS has not been issued by the R22 gates."
    Write-Host "Blocker: all official channels currently carry the PRE-#13437 MIOpen.dll"
    Write-Host "        (see windows-golden-path/reports/R22_RELEASE_GATE_MATRIX.json)."
    Write-Host "Until a post-fix stable wheel exists, there is no supported no-workaround"
    Write-Host "install path. See docs/r23/TROUBLESHOOTING.md (blocked-release documentation)."
    exit 4
}

if ($Mode -ne "EngineeringDemonstration") {
    # DEFAULT = fail closed BEFORE touching the machine (R21.1 TASK E)
    Write-Host ""
    Write-Host "STATUS (no install performed):"
    Write-Host "  stable channel : BLOCKED_OFFICIAL_ARTIFACT (MIOpen.dll pre-#13437, marker 0)"
    Write-Host "  rc channel     : BLOCKED_OFFICIAL_ARTIFACT (10.2.0rc2 branch cut before fix merge, behind_by=92)"
    Write-Host "  multi-arch 7.x : PRE-FIX (MIOpen.dll 266d716b..., marker 0)"
    Write-Host "  nightly/dev    : POST-FIX libraries exist; candidate-level only (DEV_CANDIDATE_PASS on gfx1100),"
    Write-Host "                    gfx1100 device wheels missing on nightly as of 2026-11-15"
    Write-Host ""
    Write-Host "This script will NOT install a known pre-fix release and claim normal"
    Write-Host "no-workaround training readiness. To run an explicitly labeled engineering"
    Write-Host "demonstration on the pre-fix engineering-reference stack (requires Visual"
    Write-Host "Studio Build Tools on this machine; reproduces Ultralytics issue #3956"
    Write-Host "otherwise), re-run with:"
    Write-Host "  powershell -File quickstart.ps1 -Mode EngineeringDemonstration"
    Write-Host "See windows-golden-path/reports/R22_RELEASE_GATE_MATRIX.json for gate status."
    exit 3
}

# --- explicitly labeled engineering demonstration -----------------------------
Write-Host ""
Write-Host "======================================================================="
Write-Host " ENGINEERING DEMONSTRATION — NOT a release-qualified install."
Write-Host " Stack: multi-arch 7.14.1 engineering reference (MIOpen.dll PRE-#13437)."
Write-Host " On machines WITHOUT Visual Studio Build Tools the training below is"
Write-Host " expected to fail with the documented HIPRTC 'type_traits' issue #3956."
Write-Host "======================================================================="
Write-Host ""

# 1) clean venv
& $Python -m venv "$Root\venv"
& "$Root\venv\Scripts\python.exe" -m pip install --quiet --upgrade pip

# 2) official AMD torch stack (verified pins)
& "$Root\venv\Scripts\python.exe" -m pip install `
    torch==2.12.0+rocm7.14.1 torchvision==0.27.0+rocm7.14.1 `
    --index-url https://repo.amd.com/rocm/whl-multi-arch/
if ($Gfx -eq "gfx1100") {
    & "$Root\venv\Scripts\python.exe" -m pip install `
        amd-torch-device-gfx1100==2.12.0+rocm7.14.1 `
        amd-torch-device-gfx110x==2.12.0+rocm7.14.1 `
        amd-torchvision-device-gfx1100==0.27.0+rocm7.14.1 `
        --index-url https://repo.amd.com/rocm/whl-multi-arch/
} else {
    & "$Root\venv\Scripts\python.exe" -m pip install `
        amd-torch-device-gfx1151==2.12.0+rocm7.14.1 `
        amd-torchvision-device-gfx1151==0.27.0+rocm7.14.1 `
        --index-url https://repo.amd.com/rocm/whl-multi-arch/
}

# 3) released Ultralytics
& "$Root\venv\Scripts\python.exe" -m pip install ultralytics==8.4.214

# 4) verify GPU
& "$Root\venv\Scripts\python.exe" -c "import torch; assert torch.cuda.is_available(); print('GPU OK:', torch.cuda.get_device_name(0))"

# 5) standard first training (COCO8 smoke) — expected to FAIL without VS Build Tools
New-Item -ItemType Directory -Force -Path "$Root\run1" | Out-Null
Push-Location "$Root\run1"
& "$Root\venv\Scripts\yolo.exe" train model=yolo26n.pt data=coco8.yaml epochs=1 device=-1
$code = $LASTEXITCODE
Pop-Location
Write-Host "train exit code: $code  (best.pt/last.pt under $Root\run1\runs\detect\train\weights)"
if ($code -ne 0) {
    Write-Host "Non-zero exit is the EXPECTED pre-fix behavior without VS Build Tools (issue #3956)."
    Write-Host "This exit code is a demonstration result, not a readiness claim."
}
exit $code
