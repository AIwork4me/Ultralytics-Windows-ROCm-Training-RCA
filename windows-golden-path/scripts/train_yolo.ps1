# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
<#
.SYNOPSIS
Standard Ultralytics user command gate (mission §8).

.DESCRIPTION
Runs the EXACT standard user command with zero non-default parameters:

    yolo train model=yolo26n.pt data=coco8.yaml epochs=1 device=-1

in an isolated disposable working directory, after verifying the `yolo`
executable belongs to the intended clean target venv. Captures the process
exit code, parses the log for genuine GPU selection / AMP check / completed
epoch / validation / saved checkpoints, and records checkpoint SHA256.
Diagnostic reruns must be separate invocations — this script adds nothing.

.PARAMETER VenvDir    target venv (its Scripts\yolo.exe must exist)
.PARAMETER WorkDir    disposable working directory for this run
.PARAMETER OutJson    evidence JSON path (written by the python summarizer)
.PARAMETER RunId      run id
#>
param(
    [Parameter(Mandatory = $true)][string]$VenvDir,
    [Parameter(Mandatory = $true)][string]$WorkDir,
    [Parameter(Mandatory = $true)][string]$OutJson,
    [Parameter(Mandatory = $true)][string]$RunId,
    [string]$Channel = "",
    [string]$ExtraArgs = ""
)
$ErrorActionPreference = "Continue"
$naming = "train_yolo.ps1"

$yoloExe = Join-Path $VenvDir "Scripts\yolo.exe"
$yoloPy  = Join-Path $VenvDir "Scripts\yolo.exe"
if (-not (Test-Path $yoloExe)) { Write-Error "$naming : yolo.exe not in venv $VenvDir"; exit 2 }
# executable ownership check: resolve and require under the target venv
$resolved = (Resolve-Path $yoloExe).Path
if (-not $resolved.StartsWith((Resolve-Path $VenvDir).Path, [StringComparison]::OrdinalIgnoreCase)) {
    Write-Error "$naming : yolo resolves outside target venv: $resolved"; exit 2
}
Write-Output "[$naming] yolo executable: $resolved"

New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
$log = Join-Path $WorkDir "train_stdout.log"
$cmd = "yolo train model=yolo26n.pt data=coco8.yaml epochs=1 device=-1"
if ($ExtraArgs -ne "") { $cmd = $cmd + " " + $ExtraArgs }
Write-Output "[$naming] EXACT COMMAND: $cmd"

# cmd /c gives reliable redirection + $LASTEXITCODE on PS 5.1 (Start-Process
# -PassThru with redirects loses ExitCode — verified on 5.1.26100). The run
# must execute with cwd = WorkDir so runs/ artifacts land in the disposable dir.
$argline = ($cmd -replace "^yolo ", "")
Push-Location $WorkDir
& cmd /c "`"$resolved`" $argline > `"$log`" 2>&1"
$exit = $LASTEXITCODE
Pop-Location
Write-Output "[$naming] exit code: $exit"

# checkpoint hashes (in the disposable dir's default runs/ tree)
$ckpts = @()
Get-ChildItem -Path "$WorkDir\*" -Recurse -Include "last.pt","best.pt" -ErrorAction SilentlyContinue |
    ForEach-Object {
        $ckpts += @{ path = $_.FullName; sha256 = (Get-FileHash -Algorithm SHA256 $_.FullName).Hash.ToLower();
                     bytes = $_.Length }
    }

# summarize with the harness python (strict evidence record).
# JSON goes through a FILE: PS 5.1 native-arg passing mangles embedded quotes.
$cjson = if ($ckpts -and @($ckpts).Count -gt 0) {
    ConvertTo-Json -InputObject @($ckpts) -Compress -Depth 4
} else { "[]" }
$cfile = Join-Path $WorkDir "checkpoints.json"
Set-Content -Path $cfile -Value $cjson -Encoding UTF8
$vpy = Join-Path $VenvDir "Scripts\python.exe"
$chanArg = @()
if ($Channel -ne "") { $chanArg = @("--channel", $Channel) }
& $vpy -I (Join-Path $PSScriptRoot "generate_report.py") train-summary `
    --run-id $RunId --log $log --exit-code $exit --out $OutJson `
    --checkpoints-json-file $cfile --command $cmd @chanArg
if ($LASTEXITCODE -ne 0 -and $exit -eq 0) { $exit = $LASTEXITCODE }  # summary gate fails closed
exit $exit
