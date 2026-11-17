# P19 Phase C: maintainer's EXACT second command on PR #27203 HEAD d8fe65c8
$ErrorActionPreference = "Continue"
Set-Location C:\P19\pr27203
$env:HIPRTC_COMPILE_OPTIONS_APPEND = "-IC:\Users\Rocm\Desktop\YOLO\YOLO26_ROCm_Day1_Labs\scripts\miopen_shims"
& C:\P19\venv\Scripts\python.exe -c "import sys, ultralytics, pytest; print('PYTHON=' + sys.executable); print('ULTRALYTICS=' + ultralytics.__file__); print('PYTEST=' + pytest.__version__)"
# --- exact maintainer command below (no added flags) ---
& C:\P19\venv\Scripts\pytest.exe tests/test_cuda.py > C:\P19\logs\phase_c_full_test_cuda.log 2>&1
$code = $LASTEXITCODE
"EXIT_CODE=$code"
exit $code
