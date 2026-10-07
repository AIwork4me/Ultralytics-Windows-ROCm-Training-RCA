@echo on
REM Gate 27 arms B and C: VS dev shell and INCLUDE-only injection.
REM Called with %1 = B or C. Output redirected by the caller.
set "RCA=C:\Users\rocm\Desktop\YOLO_AMD\Ultralytics-Windows-ROCm-Training-RCA"
set "ENVPY=C:\Users\rocm\miniconda3\envs\yolo_amd\python.exe"
set PYTHONNOUSERSITE=1
set "HIPRTC_CORE_BIN=C:\Users\rocm\miniconda3\envs\yolo_amd\Lib\site-packages\_rocm_sdk_core\bin"

if /I "%1"=="B" (
  call "C:\BuildTools\Common7\Tools\VsDevCmd.bat" -arch=x64 -no_logo
  echo === ARM B env delta ===
  echo INCLUDE=%INCLUDE%
  echo LIB=%LIB%
  echo VCToolsInstallDir=%VCToolsInstallDir%
)

if /I "%1"=="C" (
  REM Arm C: ONLY the INCLUDE variable injected, nothing else from the dev shell.
  set "INCLUDE=C:\BuildTools\VC\Tools\MSVC\14.44.35207\include;C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\ucrt;C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\shared;C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\um"
  echo === ARM C env delta ===
  echo INCLUDE=%INCLUDE%
)

echo === standalone HIPRTC probe ===
"%ENVPY%" "%RCA%\scripts\phase2\hiprtc_probe\hiprtc_probe.py" type_traits
echo hiprtc_probe_exit=%ERRORLEVEL%
echo === minimal BN repro ===
"%ENVPY%" "%RCA%\scripts\02_batchnorm_minimal.py" minimal
echo bn_repro_exit=%ERRORLEVEL%
