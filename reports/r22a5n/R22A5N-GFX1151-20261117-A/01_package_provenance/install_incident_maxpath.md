# R22A.5N Phase 1 — install incident record: Windows MAX_PATH (test-infrastructure, not candidate defect)

- Attempt 1: `install_official.ps1 -VenvDir C:/Users/rocm/Desktop/YOLO_AMD/r22a5n/venv ...`
  - Offline leg (`--no-index`) failed building the `rocm-10.3.0a20261116.tar.gz` sdist:
    build isolation requires `setuptools>=70.2.0` from an index. The installer's
    documented PyPI-retry path handled this (build-time dependency only; every
    runtime wheel is still local hash-verified bytes).
  - Retry leg then aborted with
    `OSError: [Errno 2] ... heuristic.uhd.json` while unpacking
    `rocm_sdk_device_gfx1151`: member
    `_rocm_sdk_libraries/bin/hipdnn_plugins/.../43c4a81e-f427-56ec-b01f-688019b91f85/predict_engine/gfx1100/tflops/heuristic.uhd.json`
    is 203 chars; site-packages prefix of that venv is 63 chars → 266 > 260
    (host `LongPathsEnabled=0`). Partial install (9 distributions) discarded.
- Root cause: Windows MAX_PATH filesystem limit × deep venv location. NOT a
  defect of the candidate wheels' contents and NOT a software workaround:
  no DLL replacement, no env-injection, no installed-package edit.
- Resolution (mission-local only): reinstall at the short mission root
  `C:\r22a5n\venv` (prefix 35 chars → deepest path 238 < 260). No global
  driver/registry/system change; `LongPathsEnabled` left untouched (0).
- Upstream-relevant caveat (for the final report): with default Windows
  settings (`LongPathsEnabled=0`), any user whose site-packages prefix
  exceeds 57 characters cannot install `rocm-sdk-device-gfx1151` 10.3.0a20261116
  at all. Typical `C:\Users\<short-name>\.venv\Lib\site-packages\` (~45) fits;
  nested project venvs commonly do not.
