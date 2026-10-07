# External evidence archive (retrieved 2026-10-07, UTC+8)

Only short relevant excerpts are archived; see each URL for full pages.

## A. ROCm/MIOpen issue #3956

- URL: https://github.com/ROCm/MIOpen/issues/3956
- Retrieval: 2026-10-07 via GitHub API (`gh api repos/ROCm/MIOpen/issues/3956`)
- Raw JSON: `miopen_3956_issue.json`, `miopen_3956_meta.json` (this directory)
- Title: "Running BatchNorm2D  causes miopenStatusUnknownError"
- State: OPEN (created 2026-04-22, label `status: triage`, 0 comments — no
  maintainer response as of retrieval)
- Reporter environment:
  - OS: Windows 11, version 25H2
  - GPU: Radeon RX 9060 XT 16GB → error says "compiling for gfx1200"
  - Python 3.12.7, PyTorch 2.9.1+rocm7.2.1, ROCm 7.2.1
- Reproducer: pure `nn.BatchNorm2d(100)`, input `(20, 100, 35, 45)` — no
  Ultralytics.
- Signature: `MIOpenBatchNormFwdTrainSpatialHIP.cpp`,
  `HIPRTC_ERROR_COMPILATION (6)`, `miopen_type_traits.hpp:151:10: fatal
  error: 'type_traits' file not found`, `1 error generated when compiling for
  gfx1200`, `hipoc_program.cpp:299: Code object build failed`,
  `RuntimeError: miopenStatusUnknownError`.
- No workaround, no Visual Studio/MSVC discussion (0 comments).

## B. AMD ROCm 7.14.0 release notes

- URL: https://rocm.docs.amd.com/en/docs-7.14.0/about/release-notes.html
- Retrieval: 2026-10-07 (WebFetch)
- "Applies to Linux and Windows." OS support: Windows 11 (25H2 column).
- Hardware table lists "Ryzen AI Max+ 395 (Radeon 8060S)" as gfx1151 /
  RDNA 3.5 — i.e. our exact APU is a supported device in this release.
- "AI ecosystem support": PyTorch 2.12.0 — Windows (only ML framework listed
  with Windows support).
- MIOpen 3.5.1 ⇒ 3.5.2; changelog mentions naive-solver skipping and conv
  fixes only. No mention of HIPRTC, runtime compilation, BatchNorm, missing
  headers, or any Visual Studio prerequisite.

## C. AMD "PyTorch via PIP installation — Windows" (Radeon/Ryzen docs)

- URL: https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/install/installrad/windows/install-pytorch.html
- Retrieval: 2026-10-07 (WebFetch; page documents the 7.2.1 flow, latest
  available at this URL)
- Install = pip install ROCm SDK wheels from
  `https://repo.radeon.com/rocm/windows/rocm-rel-*/...` then torch/
  torchaudio/torchvision `+rocm*` win_amd64 wheels from the same repo.
  This matches how our machine's stack is laid out (wheels installed into
  site-packages; `rocm_sdk_core`, `rocm_sdk_libraries` packages).
- Prerequisites stated: Python 3.12 and the 26.2.2 graphics driver.
- **No Visual Studio / MSVC / C++ build-tools requirement is documented
  anywhere on the page**, even though a `rocm_sdk_devel` wheel is installed.
- Verification stops at `torch.cuda.is_available()` / `get_device_name(0)` /
  `collect_env` — i.e. detection-level, not a BatchNorm training check.

## D. Ultralytics AMD integration docs

- URL: https://docs.ultralytics.com/integrations/amd
- Retrieval: 2026-10-07 (WebFetch)
- "This guide targets Linux x86_64 hosts with the AMD GPU kernel driver
  (amdgpu) installed"; "native Windows is not supported, and Windows
  Subsystem for Linux (WSL2) has not been validated yet."
- Training on AMD GPUs is documented via PyTorch ROCm with `device=0`;
  benchmark GPU: "AMD Radeon 8060S GPU (Ryzen AI Max+ PRO 395)" (on Linux).
- "ROCm build of PyTorch uses HIP internally but deliberately reuses the
  torch.cuda interfaces" — explains the "CUDA:0" label seen locally.
- AMP caveat: "if a run still produces NaN losses or zero mAP, train with
  amp=False" (generic ROCm advice, unrelated to this failure).

## E. ROCm/rocm-libraries issue #2169 (related, earlier instance)

- URL: https://github.com/ROCm/rocm-libraries/issues/2169
- Retrieval: 2026-10-07 via GitHub API; raw: `rocm_libraries_2169_*.txt/json`
- "[Issue]: torch.nn.BatchNorm2d fails with MIOpenBatchNormFwdTrainSpatial
  compilation error" (2025-10-19), closed 2025-10-20 as **duplicate**.
- Windows log shows the same `MIOpenBatchNormFwdTrainSpatialHIP.cpp`
  HIPRTC_ERROR_COMPILATION / `type_traits` not found signature.
- Reporter: "consistently reproducible on both Ubuntu and Windows"; noted
  "Both float32 and float16 inputs are affected, so it is probably not
  related to Automatic Mixed Precision" (independently matches our AMP
  falsification).
- Closed by reporter as duplicate of TheRock#842; reporter verified a fix in
  TheRock nightly ≥ rocm-libraries 20251016 (rocm-libraries PR #1288).

## F. ROCm/TheRock issue #842 and rocm-libraries PR #1288 (upstream fix for a
   DIFFERENT mechanism)

- URLs: https://github.com/ROCm/TheRock/issues/842 ,
  https://github.com/ROCm/rocm-libraries/pull/1288
- Retrieval: 2026-10-07 via GitHub API; raw: `therock_842_*.txt/json`,
  `rocm_libraries_pr1288.json`
- TheRock#842: "gfx1151 - error: not a valid operand using PyTorch" (Jun
  2025) — the gfx1151 OpenCL-path defect (`MIOpenBatchNormFwdTrainSpatial.cl`
  inline-asm DPP instructions), closed completed 2025-10-17.
- PR #1288 "[miopen] Add Strix Halo support to Miopen CI" (merged
  2025-10-08): "Added MIO_BN_GFX115X define to OpenCL kernels to avoid them
  using unsupported DPP instructions on gfx1151 hardware".
- Note: that fix targets the **OpenCL (.cl) compile path**; our local failure
  is the **HIPRTC (.cpp) path** failing on `#include <type_traits>` — a
  distinct mechanism, and our stack (ROCm 7.14.0 / MIOpen 3.5.2, 2026 build)
  still exhibits it.
