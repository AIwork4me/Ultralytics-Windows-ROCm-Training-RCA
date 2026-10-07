# Run the full Phase 1 RCA suite in order (environment capture -> controls ->
# repro -> matrix -> AMP/CPU falsifications -> MIOpen logging -> toolchain ->
# provenance -> artifact collection). Each step writes its own raw evidence.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File run_all_rca.ps1 [-Python ...]
param(
    [string]$Python = "C:\Users\rocm\miniconda3\python.exe",
    [string]$Yolo = "C:\Users\rocm\miniconda3\Scripts\yolo.exe",
    [string]$WorkDir = "C:\Users\rocm\Desktop\YOLO_AMD"
)
$ErrorActionPreference = "Continue"
$steps = @(
    @{ n = "00 environment baseline";   c = { & powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\00_capture_environment.ps1" -Python $Python } },
    @{ n = "01 GPU GEMM control";       c = { & $Python "$PSScriptRoot\01_gpu_gemm_control.py" *> "$PSScriptRoot\..\evidence\raw\gpu-control\gemm.txt" } },
    @{ n = "04 conv control";           c = { & $Python "$PSScriptRoot\04_conv_control.py" *> "$PSScriptRoot\..\evidence\raw\conv\conv_control.txt" } },
    @{ n = "02 batchnorm minimal x3";   c = {
        foreach ($case in "minimal", "issue3956", "yololike") {
            & $Python "$PSScriptRoot\02_batchnorm_minimal.py" $case *>
                "$PSScriptRoot\..\evidence\raw\batchnorm\minimal_$case.txt"
        } } },
    @{ n = "03 batchnorm matrix";       c = { & $Python "$PSScriptRoot\03_batchnorm_matrix.py" *> "$PSScriptRoot\..\evidence\raw\batchnorm\matrix.txt" } },
    @{ n = "05 ultralytics predict";    c = { & powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\05_ultralytics_inference_control.ps1" -Yolo $Yolo -WorkDir $WorkDir } },
    @{ n = "06 ultralytics train GPU";  c = { & powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\06_ultralytics_train_repro.ps1" -Yolo $Yolo -WorkDir $WorkDir -Tag "gpu" } },
    @{ n = "07 AMP falsification";      c = { & powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\07_ultralytics_amp_falsification.ps1" -Yolo $Yolo -WorkDir $WorkDir } },
    @{ n = "08 MIOpen logging";         c = { & powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\08_miopen_logging.ps1" -Python $Python } },
    @{ n = "09 toolchain probe";        c = { & powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\09_toolchain_probe.ps1" } },
    @{ n = "10 DLL provenance";         c = { & $Python "$PSScriptRoot\10_dll_provenance.py" *> "$PSScriptRoot\..\evidence\raw\environment\dll_provenance.txt" } },
    @{ n = "10 collect artifacts";      c = { & powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\10_collect_artifacts.ps1" } }
)
foreach ($s in $steps) {
    Write-Host "=== $($s.n) ==="
    & $s.c
    Write-Host "    (last exit: $LASTEXITCODE)"
}
Write-Host "`nRCA suite complete. Inspect docs\ and evidence\."
