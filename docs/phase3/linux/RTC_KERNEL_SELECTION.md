# Linux RTC Kernel Selection — Gate L36

Date: 2026-10-08. Method: run the Windows Phase-3 audit tool
(scripts/phase3/audit_rtc_std_dependencies.py, reused verbatim) on BOTH
Linux source trees at SOURCE_SHA b68f8944 with
MIOPEN_HIP_RUNTIME_COMPILE=1, HIP_PACKAGE_VERSION_FLAT=7140060850.

## Audit reproduction (matches Windows Gate 54 exactly)

- RTC population: 104 kernel entry files (identical set both trees)
- `<type_traits>` reachable: 32 kernels (BN families, Neuron, LRN, RNN,
  CheckNumerics, Kthvalue, ConvDirBatchNormActiv, fp8 reference convs,
  static_composable_kernel conv wrappers)
- `<utility>` reachable: 14 (static CK conv wrappers, std::forward users)
- `<initializer_list>` reachable: 6 (Getitem, Kthvalue, MultiMarginLoss,
  PReLU, ReduceSum, SoftMarginLoss)
- `<limits>` reachable: 1 (Kthvalue via radix.hpp)
- entity users recorded per header; patched tree shows the same reachable
  sets (__has_include arms recorded as probe-dependent, per the tool)

## Why each g68 matrix case exists (kernel → coverage)

| Case (g68 mirror) | RTC kernels exercised | std dependency covered |
|---|---|---|
| maxpool2d_bwd / avgpool2d_bwd / adaptive_avgpool2d | MIOpenPoolingBwd* | numeric_limits (miopen_limits) |
| prelu_fwd_bwd | MIOpenPReLU.cpp | tensor_view initializer_list probe |
| conv_depthwise/grouped/dilated/transpose/1x1 | Conv* + MIOpenConv* + static CK wrappers | type_traits (32) + utility/forward (14) |
| softmax_attn_like | MIOpenSoftmaxAttn | numeric_limits + is_trivially_copyable (hip_float8) |
| dropout2d_train | MIOpen dropout path | control |
| BN matrix (Gates L30/L34) | MIOpenBatchNormFwd/Bwd Spatial/PerAct + Activ fused | type_traits via wrapper (10 kernels) |

Kthvalue/Getitem/ReduceSum/MarginLoss families are driver-API ops not
routed by PyTorch spatial ops (torch uses its own kthvalue kernels);
covered at compile level by the audit + the wrapper/freestanding canaries
(Gate L33) instead of runtime, mirroring the Windows matrix decision.

## Result

GATE L37 (evidence/phase3/raw/linux/rtc_kernels/nonbn_matrix.txt):
unpatched 11/11 PASS → patched 11/11 PASS.
