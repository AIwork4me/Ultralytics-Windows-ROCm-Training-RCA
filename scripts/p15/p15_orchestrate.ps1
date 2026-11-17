# P15 gfx1151 orchestrator (official released stack: pm13437_official env)
# Sequence: amp-probe -> smoke legs (w0/w2/w4 fresh, w2 warm) -> 30-epoch train ->
#           interrupt after epoch >= 20 -> new-process resume -> finalcheck
$ErrorActionPreference = "Continue"
$repo = "C:\Users\rocm\Desktop\YOLO_AMD\Ultralytics-Windows-ROCm-Training-RCA"
$py = "C:\Users\rocm\miniconda3\envs\pm13437_official\python.exe"
$driver = Join-Path $repo "scripts\p15\p15_run.py"
Set-Location $repo
New-Item -ItemType Directory -Force -Path "$repo\release-provenance\raw\p15_gfx1151" | Out-Null
$runId = "p15_30ep_w2"

Write-Output "=== [1/6] amp-probe ==="
if (-not (Test-Path "$repo\release-provenance\raw\p15_gfx1151\amp_probe.json")) {
    & $py $driver amp-probe 2>&1 | Tee-Object -FilePath "$repo\release-provenance\raw\p15_gfx1151\orchestrate_amp_probe.log"
} else { Write-Output "amp_probe.json already present — skipping (evidence immutable)" }

Write-Output "=== [2/6] smoke legs ==="
foreach ($w in 0, 2, 4) {
    if (-not (Test-Path "$repo\release-provenance\raw\p15_gfx1151\p15_smoke_w$w.json")) {
        & $py $driver smoke --workers $w 2>&1 | Tee-Object -FilePath "$repo\release-provenance\raw\p15_gfx1151\orchestrate_smoke_w$w.log"
    } else { Write-Output "p15_smoke_w$w.json already present — skipping" }
}
if (-not (Test-Path "$repo\release-provenance\raw\p15_gfx1151\p15_smoke_w2_warm.json")) {
    & $py $driver smoke --workers 2 --warm 2>&1 | Tee-Object -FilePath "$repo\release-provenance\raw\p15_gfx1151\orchestrate_smoke_w2_warm.log"
} else { Write-Output "p15_smoke_w2_warm.json already present — skipping" }

Write-Output "=== [3/6] 30-epoch representative train (background) ==="
$csv = Join-Path $repo "runs\p15\$runId\results.csv"
if (Test-Path $csv) { Write-Output "ABORT: $csv already exists"; exit 1 }
$p = Start-Process -FilePath $py -ArgumentList @($driver, "train30") -WorkingDirectory $repo -PassThru -NoNewWindow -RedirectStandardOutput "$repo\release-provenance\raw\p15_gfx1151\orchestrate_train30.log" -RedirectStandardError "$repo\release-provenance\raw\p15_gfx1151\orchestrate_train30.err.log"
Write-Output "train30 PID: $($p.Id)"

Write-Output "=== [4/6] waiting for epoch >= 20, then interrupting (real process kill) ==="
$deadline = (Get-Date).AddHours(4)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 60
    if ($p.HasExited) { Write-Output "ABORT: train30 exited early code=$($p.ExitCode)"; exit 1 }
    if (Test-Path $csv) {
        $rows = (Get-Content $csv | Where-Object { $_ -match "\S" }).Count - 1  # minus header
        Write-Output ("rows={0} at {1}" -f $rows, (Get-Date -Format "HH:mm:ss"))
        if ($rows -ge 20) { break }
    }
}
if (-not $p.HasExited) {
    Write-Output "INTERRUPTING training process PID=$($p.Id) after epoch >= 20 (real interruption, not graceful)"
    Stop-Process -Id $p.Id -Force
    Start-Sleep -Seconds 10
    $still = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
    Write-Output ("process_alive_after_kill: {0}" -f ($null -ne $still))
}
$last = Join-Path $repo "runs\p15\$runId\weights\last.pt"
Write-Output ("last.pt_exists: {0}" -f (Test-Path $last))

Write-Output "=== [5/6] new-process resume ==="
& $py $driver resume --run-id $runId 2>&1 | Tee-Object -FilePath "$repo\release-provenance\raw\p15_gfx1151\orchestrate_resume.log"

Write-Output "=== [6/6] finalcheck (val + reload + inference) ==="
& $py $driver finalcheck --run-id $runId 2>&1 | Tee-Object -FilePath "$repo\release-provenance\raw\p15_gfx1151\orchestrate_finalcheck.log"

Write-Output "=== ORCHESTRATION COMPLETE ==="
