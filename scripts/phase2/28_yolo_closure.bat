@echo off
REM Gate 36: fresh-shell restart validation. Run in a BRAND-NEW cmd process
REM (no inherited state). Arm 1: no candidate-required env vars (tests the
REM MSVC auto-discovery route). Arm 2: explicit test that nothing transient
REM from the Phase-2 session is required.
set "RCA=C:\Users\rocm\Desktop\YOLO_AMD\Ultralytics-Windows-ROCm-Training-RCA"
set "ENVPY=C:\Users\rocm\miniconda3\envs\yolo_amd\python.exe"
set PYTHONNOUSERSITE=1
REM scrub any session leftovers that could masquerade as requirements
set ROCM_PATH=
set MIOPEN_TEMP_DIR=
set AMD_COMGR_SAVE_TEMPS=
set MIOPEN_USER_DB_PATH=
echo === fresh-shell identity ===
echo CONDA_DEFAULT_ENV=%CONDA_DEFAULT_ENV%
"%ENVPY%" -c "import sys; print('exe:', sys.executable)"
echo === minimal BN in fresh shell, no env crutches ===
"%ENVPY%" "%RCA%\scripts\02_batchnorm_minimal.py" minimal
echo bn_exit=%ERRORLEVEL%
echo === YOLO train in fresh shell (default amp) ===
cd /d C:\Users\rocm\Desktop\YOLO_AMD
"%ENVPY%" -c "from ultralytics import YOLO; YOLO('yolo26n.pt').train(data='coco8.yaml', epochs=1, imgsz=640, device=0, workers=0)"
echo yolo_exit=%ERRORLEVEL%
