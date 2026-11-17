# P19 Phase B: maintainer's EXACT command on PR #27203 HEAD d8fe65c8
# Run from C:\P19\scratch (isolated CWD; weights/runs resolve under here)
$ErrorActionPreference = "Continue"
Set-Location C:\P19\scratch
$env:HIPRTC_COMPILE_OPTIONS_APPEND = "-IC:\Users\Rocm\Desktop\YOLO\YOLO26_ROCm_Day1_Labs\scripts\miopen_shims"
& C:\P19\venv\Scripts\python.exe -c "import sys; print('PYTHON=' + sys.executable)"
& C:\P19\venv\Scripts\python.exe -c "import ultralytics; print('ULTRALYTICS=' + ultralytics.__file__)"
# --- exact maintainer command below (no added args) ---
& C:\P19\venv\Scripts\yolo.exe train model=yolo26n.pt data=coco8.yaml epochs=1 device=-1 > C:\P19\logs\phase_b_maintainer_train.log 2>&1
$code = $LASTEXITCODE
"EXIT_CODE=$code"
exit $code
