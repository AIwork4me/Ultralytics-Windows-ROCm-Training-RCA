# P16 NVIDIA UX PARITY RESULTS (2026-11-15)

Per mission §6.2: a real Windows NVIDIA host is required for the pre-registered parity comparison (14 dimensions A–N against the frozen P15 contract).

## Verdict: NVIDIA_COMPARISON_BLOCKED_HARDWARE

No Windows NVIDIA host is available in this environment (`nvidia-smi` absent; `torch.cuda.device_count()` enumerates only the AMD HIP iGPU; no NVIDIA adapter present in `Win32_VideoController`).

**No simulated NVIDIA numbers were produced** (mission prohibition). The pre-registered parity contract (frozen P15) and the 14-dimension comparison plan remain ready to execute on any provided NVIDIA Windows host:

A. Official installation procedure · B. `yolo train` CLI · C. Python API · D. `device=0` handling · E. Model loading · F. True AMP · G. Genuine parameter updates · H. val/predict · I. Checkpoint save/reload · J. Interrupted-process resume · K. Error reporting · L. Hidden manual interventions (must be 0) · M. Repeatability · N. Reliability.

## What P16 could establish without the NVIDIA host

- **Radeon-side UX semantics were pinned against the actual upstream code paths** (PR #27203): `device=-1` idle auto-selection, `CUDA_VISIBLE_DEVICES` translation, and CUDA-generic gates now behave identically in source terms on HIP and CUDA hosts — the PR's own tests run on CPU CI (NVIDIA-equivalent non-AMD path) and the hardware legs run on gfx1151.
- **The Radeon UX parity blockers are external and precisely identified**: (1) no official fixed package (BLOCKED_RELEASE), (2) no second Radeon class (BLOCKED_HARDWARE), (3) no NVIDIA Windows host (this file), (4) no independent tester (see P16_INDEPENDENT_USER_ACCEPTANCE.md).
