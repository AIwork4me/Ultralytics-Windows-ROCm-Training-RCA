# Environment — final-HEAD validation round (2026-10-15)

Captured live on the validation machine immediately before the runs; these
are measured values, not assumed ones.

## Platform
- OS: Windows 11 Pro, build 10.0.26200.9457, x64 (`cmd /c ver`)
- APU: AMD Ryzen AI MAX+ 395
- GPU: AMD Radeon(TM) 8060S Graphics — gfx1151
  (torch `get_device_capability` = (11, 5); MIOpen live device query logs
  `Raw device name: gfx1151` and compiles every RTC kernel with
  `-mcpu=gfx1151`)
- A "GameViewer Virtual Display Adapter" also enumerates (vendor streaming
  driver); it is not a compute device.

## Software stack
- Python env: `miniconda3/envs/yolo_amd`, Python 3.13.16
- PyTorch: 2.12.0+rocm7.14.0 (torch.version.hip 7.14.60850)
- Ultralytics: 8.4.174
- HIP runtime: `C:\Windows\SYSTEM32\amdhip64_7.dll`
- Build toolchain (from `raw/build/toolchain.txt`):
  - Clang 23.0.0 (wheel `_rocm_sdk_core/lib/llvm/bin`; GNU-like CLI)
  - CMake 4.4.4, Ninja (phase3_buildtools venv)
  - MSVC Build Tools 14.44 present at `C:\BuildTools` (ambient-STL provider
    for the with-STL control legs; NOT required by the no-STL path)
- Runtime compiler: HIPRTC v.9.0 via hiprtc0714.dll / amd_comgr.dll from the
  same wheel stack

## Wheel baseline
- Pristine wheel MIOpen.dll SHA256
  `74b4ee038803606e6ea4846362a8565fa9e286cb0df18cf80b9e5a7657b78f0a`
  (verified before the swap and restored + re-verified after the D/F runs)

## Trees used this round
- Patched source: worktree `C:\w56` @ `f0f330c4` (clean), fresh build `C:\bfin`
- Negative control: worktree `C:\wp` @ `b8cf0e7b` (clean) + only
  `projects/miopen/test/gtest/hiprtc_selfcontained.cpp` present as an
  untracked file, byte-identical (LF-normalized SHA256
  `04fdffa6df8f6019e1e13dbf8a1aaba5721157e5241a3cc79d6b6ecbccf98497`) to
  the blob at `f0f330c4`; existing build tree `C:\bwp` incrementally
  relinked only that test target.
