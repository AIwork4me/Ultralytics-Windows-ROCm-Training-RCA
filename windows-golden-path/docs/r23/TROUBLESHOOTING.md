# Troubleshooting (Windows Golden Path)

User-facing symptoms → root cause → fix. Engineering workarounds live ONLY
here (appendix), never in the primary path.

## 1. `HIPRTC_ERROR_COMPILATION (6)` / `'type_traits' file not found` / `miopenStatusUnknownError`

- **Cause:** official Windows MIOpen.dll predates PR #13437 (rocm-libraries
  #15862); MIOpen's HIPRTC kernels include host MSVC STL headers that do not
  exist on machines without VS Build Tools.
- **Status:** BLOCKED_RELEASE for stable channels (10.1.0 stable / 7.14.1
  multi-arch / **10.2.0rc2 rc — proven pre-fix 2026-11-15 by marker=0 AND
  ancestry `f0a5d266...8faffed0f` behind_by=92**).
- **User fix:** none yet — wait for a post-fix wheel (watch the rc/stable
  channels; the dev channel already builds from post-fix source).
- **Engineering workaround (NOT the golden path):** freestanding-header shim
  via `HIPRTC_COMPILE_OPTIONS_APPEND` — any environment using it is classified
  ENGINEERING_REFERENCE by this harness automatically.

## 2. `torchvision.ops.nms` → `hipErrorInvalidDeviceFunction`

- **Cause:** missing `amd-torchvision-device-gfxXXXX` wheel (AMD split-wheel
  packaging; P18/P19 evidence). NOT a MIOpen regression.
- **Fix:** install the torchvision device wheel for your GPU
  (`amd-torchvision-device-gfx1100` on RX 7900 XTX). The harness classifies
  this exact case as `TORCHVISION_DEVICE_WHEEL_MISSING`.

## 3. Silent garbage output / SDPA corruption with per-arch wheel only

- **Cause:** `torch[device-gfxXXXX]` needs BOTH the per-arch device wheel AND
  the family wheel (e.g. `amd-torch-device-gfx110x`); missing family wheel
  produced silent SDPA garbage historically (P18 trap).
- **Fix:** install the full device wheel set; `resolve_package_set.py`
  enforces this in the lock.

## 4. `torch.cuda.is_available()` False with correct driver

- **Cause:** CPU-only torch wheel silently installed (wrong index).
- **Fix:** install torch from the official AMD index;
  `verify_environment`/`verify_provenance` refuse non-`+rocm` builds.

## 5. Resume fails to find `last.pt`

- Resume needs `last.pt` from the interrupted run (not `best.pt`) and
  `resume=True`; weights-only loading is NOT training-state recovery.
  `verify_checkpoint_resume.py` enforces exactly this.

## 6. MIOpen cache weirdness after experiments

- Never delete the user's global cache. Tests needing a cold cache use a
  per-run fresh `USERPROFILE` (see `verify_miopen_nostl.py`, `run_stability.py
  --cold`).

## Known NOT supported / not promised

TensorRT on AMD; ONNX Runtime `CUDAExecutionProvider` on AMD (PyPI onnxruntime
has no ROCm Windows build — the P19 `test_onnx_dynamic_spatial_outputs` failure
is this, not a YOLO bug); NVIDIA performance parity; untested gfx archs.
