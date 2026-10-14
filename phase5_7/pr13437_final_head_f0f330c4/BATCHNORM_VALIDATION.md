# BatchNorm Validation — patched wheel DLL (leg D)

## Reproducer
Mission-spec minimal reproducer, executed as `scripts/d_batchnorm.py`
(archived verbatim) with the pinned-build MIOpen.dll swapped into the wheel:

- `nn.BatchNorm2d(100)` (affine, default eps/momentum), training mode, CUDA
- input `torch.randn(20, 100, 35, 45)` FP32, `requires_grad=True`
- forward → `y.square().mean()` → backward
- CPU reference: same seed (`torch.manual_seed(0)`, CUDA generator seed 1234),
  same state_dict, training-mode semantics; running stats recomputed from
  the momentum update rule on the CPU copy of the input.

## Runtime-binary provenance
- Executed **twice** with the same swap protocol; the second run (v2) is the
  primary evidence and carries a UTC banner for freshness.
- Archived swap transcript (`raw/batchnorm/swap_transcript_v2.log`) records
  the hash sequence at the wheel path: `74b4ee03…` (pre-swap pristine) →
  `c739cb0e143162694c331ef8137e686418d003769ed7ad25c96945fe63a6fb42`
  (pinned `f0f330c4` build swapped in) → `74b4ee03…` (restored), plus the
  backup-file hash.
- In-process `GetModuleFileNameA` proof (in both run logs):
  `MIOpen.dll loaded from: …site-packages\_rocm_sdk_libraries\bin\MIOpen.dll`

## Results (raw: `raw/batchnorm/D_batchnorm_patched_v2.log`, exit 0; identical numerics in run 1, kept as `D_batchnorm_patched_run1.log`)

| Quantity | Finite | max abs err vs CPU reference |
|---|---|---|
| output y | yes | 9.537e-07 |
| grad x | yes | 1.174e-12 |
| grad weight | yes | 5.588e-09 |
| grad bias | yes | 6.580e-10 |
| running_mean | yes | 6.985e-10 |
| running_var | yes | 3.338e-06 |

Tolerance policy: PASS requires all values finite and every max-abs error
< 1e-3 (FP32 GPU-vs-CPU; running_var carries the expected larger-but-small
error of the momentum-blended update). `BATCHNORM_VALIDATION: PASS`.

The errors are **identical to the pre-squash R2 round** and to both runs of
this round (same seeds, same deterministic kernels — the script's every
printed line is deterministic, so run 1's log is byte-identical to R2's D
log; that byte-identity is expected, disclosed here, and is why the v2 run
adds the UTC banner as the fresh-run discriminator). An independent
cross-check that the final committed code produces the same numerics as the
previously validated working tree.

## What this exercises
Spatial BatchNorm on GPU routes through MIOpen, which runtime-compiles
`MIOpenBatchNormFwdTrainSpatial.cpp` via HIPRTC — the exact workload class
that crashed with `'type_traits' file not found` before the fix. Forward and
backward both completed with finite, reference-consistent values, and no
MIOpen compile error appears in the log.
