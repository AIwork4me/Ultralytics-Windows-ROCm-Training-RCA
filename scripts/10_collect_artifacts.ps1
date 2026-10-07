# Phase 16: collect evidence artifacts -> manifest.json + SHA256SUMS.txt.
# Hashes every file under evidence/raw and evidence/normalized (excluding
# the outputs of this script itself). Read-only w.r.t. raw logs.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File 10_collect_artifacts.ps1
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

$targets = @()
foreach ($root in @("evidence\raw", "evidence\normalized")) {
    $targets += Get-ChildItem -Recurse -File $root |
        Where-Object { $_.Name -notin @("manifest.json", "SHA256SUMS.txt") }
}

$manifest = @()
foreach ($f in $targets) {
    $hash = (Get-FileHash -Algorithm SHA256 $f.FullName).Hash.ToLower()
    $rel = $f.FullName.Substring($RepoRoot.Length + 1) -replace "\\", "/"
    # First "### command:" line inside the file, if any.
    $cmd = ""
    $m = Select-String -Path $f.FullName -Pattern "^###? command:(.*)$" | Select-Object -First 1
    if ($m) { $cmd = $m.Matches[0].Groups[1].Value.Trim() }
    $manifest += [ordered]@{
        path       = $rel
        timestamp  = $f.LastWriteTimeUtc.ToString("o")
        command    = $cmd
        sha256     = $hash
        size_bytes = $f.Length
    }
}

$manifest | ConvertTo-Json -Depth 4 | Out-File "evidence\manifest.json" -Encoding utf8

$lines = foreach ($m in $manifest) { "$($m.sha256)  $($m.path)" }
# LF endings + no BOM so `sha256sum -c` works on POSIX systems too.
[IO.File]::WriteAllText("$RepoRoot\evidence\SHA256SUMS.txt",
    (($lines -join "`n") + "`n"),
    (New-Object System.Text.UTF8Encoding($false)))

Write-Host ("collected {0} evidence files; wrote evidence\manifest.json and evidence\SHA256SUMS.txt" -f $manifest.Count)
