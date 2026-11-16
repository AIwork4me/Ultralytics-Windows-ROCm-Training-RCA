# Community release summary (R23 DRAFT — hold until R22 OFFICIAL_STABLE_PASS)

**Train YOLO on Windows with AMD Radeon — official packages, one command.**

If you have an RX 7900 XTX or a Radeon 8060S on Windows 11, installing the
official AMD PyTorch wheels + `pip install ultralytics==8.4.214` gives you
working `yolo train … device=-1` GPU training, AMP, checkpoints and resume —
no source builds, no DLL surgery, no AMD internals.

**Status (2026-11-15): hold.** The last remaining piece is a stable-channel
ROCm wheel carrying the MIOpen Windows fix (merged upstream 2026-10-19,
already flowing in AMD's dev/nightly channels; every stable and rc wheel
audited today is still pre-fix — including ROCm 10.2.0rc2, which was built
after the merge date from a branch that predates it). Until that wheel ships,
machines without Visual Studio Build Tools will hit a HIPRTC `'type_traits'
file not found` error at the first BatchNorm. Tracking:
[ROCm/rocm-libraries#15862](https://github.com/ROCm/rocm-libraries/issues/15862).

When it ships, this repo's one-command harness re-validates the full path
(install → GPU detect → train → AMP → resume → stability) on both
architectures before the guide goes public.

Not promised: NVIDIA-equal speed, TensorRT, ONNX-runtime CUDA-EP on AMD.
